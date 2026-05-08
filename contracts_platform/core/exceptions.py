class ContractPlatformError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ContractNotFoundError(ContractPlatformError):
    pass


class ClauseExtractionError(ContractPlatformError):
    pass


class DatabaseError(ContractPlatformError):
    pass


class StorageError(ContractPlatformError):
    pass


class AuthenticationError(ContractPlatformError):
    pass


class AuthorizationError(ContractPlatformError):
    pass


class FileValidationError(ContractPlatformError):
    pass


class DuplicateContractError(ContractPlatformError):
    def __init__(self, message: str, existing_contract_id: str) -> None:
        super().__init__(message)
        self.existing_contract_id = existing_contract_id


class OCRError(ContractPlatformError):
    pass


class LLMError(ContractPlatformError):
    pass
