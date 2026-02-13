from dify_plugin import ToolProvider


class DoubaoArkVideoProvider(ToolProvider):
    def validate_credentials(self, credentials: dict) -> None:
        # Required fields are enforced by schema; keep validation lightweight.
        return

    def _validate_credentials(self, credentials: dict) -> None:
        # Backward-compatible hook if the runtime calls the private method.
        return
