from ListManagement.config import Config

con = Config()


def is_bad_extension(item):
    if item.exentsion not in con.ACCEPTED_FILE_TYPES:
        item.bad_extension = True
    return item
