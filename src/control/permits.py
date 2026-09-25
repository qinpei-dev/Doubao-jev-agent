"""In-memory, single-use permit authority bound to action content."""

from datetime import datetime, timedelta, timezone

from .models import ActionProposal, ControlDecision, DecisionOutcome, ExecutionPermit


class PermitError(PermissionError):
    pass


class ExecutionPermitAuthority:
    def __init__(self, ttl: timedelta = timedelta(minutes=1)) -> None:
        if ttl <= timedelta(0):
            raise ValueError("permit TTL must be positive")
        self.ttl = ttl
        self._issued: dict[str, tuple[str, str, str, DecisionOutcome, str, datetime]] = {}

    def issue(
        self,
        proposal: ActionProposal,
        decision: ControlDecision,
        approval_source: str,
    ) -> ExecutionPermit:
        if decision.action_id != proposal.action_id:
            raise PermitError("decision does not match the action")
        if decision.proposal_digest != proposal.digest():
            raise PermitError("decision does not match the action contents")
        if (
            decision.outcome == DecisionOutcome.ALLOW
            and (decision.source, approval_source) in {("jev", "jev"), ("policy", "policy")}
        ):
            approved = True
        elif (
            decision.outcome == DecisionOutcome.REVIEW
            and approval_source == "caller"
            and decision.source == "caller"
        ):
            approved = True
        else:
            raise PermitError("only an allowed decision or explicit caller approval can issue a permit")

        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + self.ttl
        permit = ExecutionPermit(
            action_id=proposal.action_id,
            tool=proposal.tool,
            decision=decision.outcome,
            approved=approved,
            approval_source=approval_source,
            proposal_digest=proposal.digest(),
            issued_at=issued_at,
            expires_at=expires_at,
        )
        self._issued[permit.permit_id] = (
            proposal.action_id,
            proposal.digest(),
            proposal.tool,
            decision.outcome,
            approval_source,
            expires_at,
        )
        return permit

    def consume(self, proposal: ActionProposal, permit: ExecutionPermit | None) -> None:
        if permit is None:
            raise PermitError("an execution permit is required")
        if not permit.approved:
            raise PermitError("execution permit is not approved")
        issued = self._issued.get(permit.permit_id)
        expected = (
            proposal.action_id,
            proposal.digest(),
            proposal.tool,
            permit.decision,
            permit.approval_source,
            permit.expires_at,
        )
        if (
            issued is None
            or issued != expected
            or permit.action_id != proposal.action_id
            or permit.tool != proposal.tool
            or permit.proposal_digest != proposal.digest()
        ):
            raise PermitError("permit is invalid or does not match this action")
        if datetime.now(timezone.utc) >= permit.expires_at:
            del self._issued[permit.permit_id]
            raise PermitError("execution permit has expired")
        del self._issued[permit.permit_id]

    def revoke(self, permit: ExecutionPermit) -> None:
        """Discard a permit when a final policy recheck changes the outcome."""
        self._issued.pop(permit.permit_id, None)
