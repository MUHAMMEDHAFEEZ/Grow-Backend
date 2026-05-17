import os


ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png", ".zip"}
MAX_FILE_SIZE = 20 * 1024 * 1024


def validate_file_size(file):
    if file.size > MAX_FILE_SIZE:
        return False, "File size exceeds 20MB limit."
    return True, None


def validate_file_extension(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' is not allowed."
    return True, None


def validate_mime_type(file):
    try:
        import magic
    except ImportError:
        return True, None

    mime = magic.from_buffer(file.read(2048), mime=True)
    file.seek(0)

    ext_map = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".zip": "application/zip",
    }

    ext = os.path.splitext(file.name)[1].lower()
    expected_mime = ext_map.get(ext)

    if expected_mime and mime != expected_mime:
        return False, f"File MIME type '{mime}' does not match extension '{ext}'."

    return True, None


def validate_upload(file):
    for validator in [validate_file_size, validate_file_extension, validate_mime_type]:
        is_valid, error = validator(file)
        if not is_valid:
            return False, error
    return True, None
