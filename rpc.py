"""Backward-compatible entrypoint for Discord RPC core."""

from rpc.discord_ipc import ActivityType, ClientRPC, OperationCode

__all__ = ["ActivityType", "ClientRPC", "OperationCode"]
