# import threading
# from intel.service import IntelAPI
import os
import shutil

dest = r'C:\Temp\Data\Intel\list_uploads'


def init_intel_processing(path, source):
    # intel = IntelAPI(path, source)
    # background_thread = threading.Thread(target=intel.scan, kwargs={'extract': True})
    # background_thread.start()
    try:
        filename, ext = os.path.basename(path), os.path.split(os.path.basename(path))[-1]
        shutil.move(path, os.path.join(dest, source + '.' + ext))
    except (FileNotFoundError):
        pass
