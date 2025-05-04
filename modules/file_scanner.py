import os
import pickle
import h5py
import magic

def detect_file_type(file_path):
    """
    Detect file type based on magic signatures.
    """
    mime = magic.Magic(mime=True)
    return mime.from_file(file_path)


def is_pickle_file(file_path):
    """
    Basic check if file is a Python pickle.
    """
    try:
        with open(file_path, 'rb') as f:
            obj = pickle.load(f)
        return obj
    except Exception:
        return None

def scan_model_file(uploaded_file):
    """
    Scans an uploaded model file for common security risks.
    """
    temp_path = f"temp_upload/{uploaded_file.name}"
    os.makedirs("temp_upload", exist_ok=True)
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    results = {
        "filename": uploaded_file.name,
        "file_type": "Unknown",
        "framework": "Unknown",
        "risks_detected": []
    }

    try:
        # Detect file type
        results["file_type"] = detect_file_type(temp_path)

        obj = is_pickle_file(temp_path)

        if obj is not None:
            # Pickle file detected
            if hasattr(obj, "predict") and hasattr(obj, "fit"):
                results["framework"] = "Pickle/Sklearn"
            else:
                results["framework"] = "Pickle/Unknown"
            results["risks_detected"].append("⚠️ Unsafe Pickle Deserialization Risk")

        elif temp_path.endswith(".h5"):
            with h5py.File(temp_path, 'r') as f:
                if 'model_config' in f.keys():
                    results["framework"] = "TensorFlow/Keras"

        elif temp_path.endswith((".pt", ".pth")):
            results["framework"] = "PyTorch"

    except Exception as e:
        results["risks_detected"].append(f"Error during scanning: {str(e)}")

    finally:
        os.remove(temp_path)

    return results

