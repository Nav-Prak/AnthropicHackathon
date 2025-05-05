import os
import pickle
import h5py
import magic
import subprocess
import io
import builtins

class RestrictedUnpickler(pickle.Unpickler):
    # only these built‑in types are allowed
    SAFE_BUILTINS = {
        'dict', 'list', 'tuple', 'set', 'frozenset',
        'str', 'bytes', 'int', 'float', 'complex', 'bool'
    }

    def find_class(self, module, name):
        # Only allow safe builtins
        if module == "builtins" and name in self.SAFE_BUILTINS:
            return getattr(builtins, name)
        raise pickle.UnpicklingError(f"Global '{module}.{name}' is forbidden")

def safe_loads(data: bytes):
    return RestrictedUnpickler(io.BytesIO(data)).load()

def detect_file_type(file_path):
    mime = magic.Magic(mime=True)
    return mime.from_file(file_path)

def is_pickle_file(file_path):
    try:
        with open(file_path, "rb") as f:
            magic_bytes = f.read(2)
        return magic_bytes == b'\x80\x04'  # Common pickle header
    except:
        return False

def disassemble_binary(file_path):
    try:
        result = subprocess.run(["objdump", "-d", file_path], capture_output=True, text=True, timeout=10)
        return result.stdout if result.returncode == 0 else "Disassembly failed."
    except Exception as e:
        return f"Error during disassembly: {str(e)}"

def scan_model_file(uploaded_file):
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
        results["file_type"] = detect_file_type(temp_path)

        if results["file_type"] in ["application/x-dosexec", "application/x-executable", "application/x-mach-binary"]:
            results["framework"] = "Native Binary"
            results["assembly"] = disassemble_binary(temp_path)
            results["risks_detected"].append("⚠️ Native binary detected - potential malware or unknown executable")

        elif is_pickle_file(temp_path):
            try:
                # read raw bytes
                with open(temp_path, 'rb') as f:
                    raw = f.read()
                # safely unpickle
                obj = safe_loads(raw)

                # detect framework as before
                if hasattr(obj, "predict") and hasattr(obj, "fit"):
                    results["framework"] = "Pickle/Sklearn"
                else:
                    results["framework"] = "Pickle/Unknown"

                # still flag that unpickling happened
                results["risks_detected"].append("⚠️ Unsafe Pickle Deserialization Risk")

            except pickle.UnpicklingError as e:
                results["risks_detected"].append(f"⛔ Unsafe pickle contents: {e}")
            except Exception as e:
                results["risks_detected"].append(f"Error processing pickle: {e}")

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
