from kivy.utils import platform


def request_storage_permissions():
    if platform == 'android':
        from android.permissions import request_permissions, Permission # type: ignore
        request_permissions([Permission.READ_EXTERNAL_STORAGE])
    elif platform == 'ios':
        # TODO: handle iOS or desktop cases if needed 
        pass
    else:
        # For desktop platforms, no permissions are needed
        pass