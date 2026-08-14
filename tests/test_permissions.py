from backend.permissions import PermissionLevel, PermissionManager


def test_permission_grant_and_check() -> None:
    manager = PermissionManager()
    manager.grant("router.manage", PermissionLevel.WRITE)
    assert manager.check("router.manage", PermissionLevel.READ)
    assert manager.check("router.manage", PermissionLevel.WRITE)
    assert not manager.check("router.manage", PermissionLevel.PRIVILEGED)


def test_permission_revoke() -> None:
    manager = PermissionManager()
    manager.grant("device.control", "write")
    assert manager.check("device.control", PermissionLevel.WRITE)
    assert manager.revoke("device.control")
    assert not manager.check("device.control")
