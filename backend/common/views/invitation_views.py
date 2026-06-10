"""Organization invitation flow: invite a person by email, they accept.

Add Member creates a pending OrgInvitation and emails an accept link instead of
trying to create a user directly (which failed for any email that already had an
account). Accepting auto-creates a passwordless account if needed and attaches a
Profile to the org with the invited role.
"""

from datetime import timedelta

from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common import serializer as common_serializer
from common.models import OrgInvitation, Profile, User
from common.serializer import (
    CreateInvitationSerializer,
    OrgAwareRefreshToken,
    OrgInvitationSerializer,
)

INVITE_TTL_DAYS = 7


def _require_org_admin(request):
    """Return an error Response if the caller can't manage members, else None."""
    profile = getattr(request, "profile", None)
    if not profile:
        return Response(
            {"error": True, "errors": "Organization context required"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if profile.role != "ADMIN" and not request.user.is_superuser:
        return Response(
            {"error": True, "errors": "Permission Denied"},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


class OrgInvitationListCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["invitations"])
    def get(self, request):
        denied = _require_org_admin(request)
        if denied:
            return denied
        invites = OrgInvitation.objects.filter(
            org=request.profile.org, status=OrgInvitation.STATUS_PENDING
        )
        return Response(
            {"error": False, "invitations": OrgInvitationSerializer(invites, many=True).data}
        )

    @extend_schema(tags=["invitations"], request=CreateInvitationSerializer)
    def post(self, request):
        denied = _require_org_admin(request)
        if denied:
            return denied

        ser = CreateInvitationSerializer(data=request.data)
        if not ser.is_valid():
            return Response(
                {"error": True, "errors": ser.errors}, status=status.HTTP_400_BAD_REQUEST
            )
        email = ser.validated_data["email"]
        role = ser.validated_data["role"]
        org = request.profile.org

        # Already a member of THIS org?
        if Profile.objects.filter(user__email__iexact=email, org=org).exists():
            return Response(
                {"error": True, "errors": f"{email} is already a member of this organization."},
                status=status.HTTP_409_CONFLICT,
            )

        # Pending invite already out for this email + org?
        if OrgInvitation.objects.filter(
            org=org, email__iexact=email, status=OrgInvitation.STATUS_PENDING
        ).exists():
            return Response(
                {
                    "error": True,
                    "errors": f"An invitation is already pending for {email}. Use Resend to send it again.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        invite = OrgInvitation.objects.create(
            org=org,
            email=email,
            role=role,
            invited_by=request.user,
            expires_at=timezone.now() + timedelta(days=INVITE_TTL_DAYS),
        )
        from common.tasks import send_org_invitation_email

        send_org_invitation_email.delay(str(invite.id))
        return Response(
            {"error": False, "message": f"Invitation sent to {email}.",
             "invitation": OrgInvitationSerializer(invite).data},
            status=status.HTTP_201_CREATED,
        )


class InvitationDetailView(APIView):
    """Revoke (delete) a pending invitation."""

    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["invitations"])
    def delete(self, request, pk):
        denied = _require_org_admin(request)
        if denied:
            return denied
        invite = OrgInvitation.objects.filter(id=pk, org=request.profile.org).first()
        if not invite:
            return Response(
                {"error": True, "errors": "Invitation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        invite.status = OrgInvitation.STATUS_REVOKED
        invite.save(update_fields=["status"])
        return Response({"error": False, "message": "Invitation revoked."})


class InvitationResendView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["invitations"])
    def post(self, request, pk):
        denied = _require_org_admin(request)
        if denied:
            return denied
        invite = OrgInvitation.objects.filter(
            id=pk, org=request.profile.org, status=OrgInvitation.STATUS_PENDING
        ).first()
        if not invite:
            return Response(
                {"error": True, "errors": "Pending invitation not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        invite.expires_at = timezone.now() + timedelta(days=INVITE_TTL_DAYS)
        invite.save(update_fields=["expires_at"])
        from common.tasks import send_org_invitation_email

        send_org_invitation_email.delay(str(invite.id))
        return Response({"error": False, "message": f"Invitation resent to {invite.email}."})


class AcceptInvitationView(APIView):
    """Public: look up an invitation by token (GET) and accept it (POST).

    No auth / no org context — the invitee isn't a member yet. Path is exempt
    from RequireOrgContext middleware.
    """

    permission_classes = []
    authentication_classes = []

    def _valid_pending(self, token):
        if not token:
            return None
        invite = (
            OrgInvitation.objects.select_related("org")
            .filter(token=token, status=OrgInvitation.STATUS_PENDING)
            .first()
        )
        if not invite or invite.is_expired:
            return None
        return invite

    @extend_schema(tags=["invitations"])
    def get(self, request):
        invite = self._valid_pending(request.query_params.get("token"))
        if not invite:
            return Response(
                {"error": True, "errors": "This invitation is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "error": False,
                "email": invite.email,
                "role": invite.get_role_display(),
                "org_name": invite.org.name,
            }
        )

    @extend_schema(tags=["invitations"])
    def post(self, request):
        from django.contrib.auth.hashers import make_password
        import secrets

        token = request.data.get("token")
        invite = self._valid_pending(token)
        if not invite:
            return Response(
                {"error": True, "errors": "This invitation is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = invite.org

        # Get or create the user (passwordless — matches magic-link signup).
        user = User.objects.filter(email__iexact=invite.email).first()
        if not user:
            user = User.objects.create(
                email=invite.email.lower(),
                password=make_password(secrets.token_urlsafe(32)),
                is_active=True,
            )
            from common.tasks import send_welcome_email

            send_welcome_email.delay(str(user.id))

        # Set RLS org context before any org-scoped writes triggered by Profile.
        if connection.vendor == "postgresql":
            with connection.cursor() as cur:
                cur.execute("SELECT set_config('app.current_org', %s, false)", [str(org.id)])

        profile = Profile.objects.filter(user=user, org=org).first()
        if not profile:
            profile = Profile.objects.create(
                user=user,
                org=org,
                role=invite.role,
                is_active=True,
                is_organization_admin=(invite.role == "ADMIN"),
                has_sales_access=True,
                has_marketing_access=True,
                date_of_joining=timezone.now().date(),
            )

        invite.status = OrgInvitation.STATUS_ACCEPTED
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["status", "accepted_at"])

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        jwt = OrgAwareRefreshToken.for_user_and_org(user, org, profile)
        return Response(
            {
                "error": False,
                "access_token": str(jwt.access_token),
                "refresh_token": str(jwt),
                "user": common_serializer.UserSerializer(user).data,
                "current_org": {"id": str(org.id), "name": org.name},
            },
            status=status.HTTP_200_OK,
        )
