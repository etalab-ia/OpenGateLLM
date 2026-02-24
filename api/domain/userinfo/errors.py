from dataclasses import dataclass


@dataclass
class UserIsNotAdminError:
    pass


@dataclass
class UserCanNotReadRoutersError:
    pass
