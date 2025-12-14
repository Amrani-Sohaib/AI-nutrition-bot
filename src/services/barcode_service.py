import logging
from PIL import Image
import cv2
import zxingcpp

# Try to import pyzbar, handle failure gracefully
try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except (ImportError, OSError) as e:
    logging.warning(f"Pyzbar not available: {e}.")
    PYZBAR_AVAILABLE = False

def decode_barcode(image_path: str) -> str:
    """
    Decodes a barcode from an image file.
    Returns the barcode number as a string, or None if not found.
    """
    logging.info(f"Scanning image: {image_path}")

    # Method 1: ZXing-CPP (New, robust)
    try:
        img = cv2.imread(image_path)
        if img is not None:
            results = zxingcpp.read_barcodes(img)
            for result in results:
                if result.text:
                    logging.info(f"ZXing detected: {result.text}")
                    return result.text
    except Exception as e:
        logging.error(f"ZXing error: {e}")

    # Method 2: Pyzbar (Best for 1D barcodes if installed)
    if PYZBAR_AVAILABLE:
        try:
            img_pil = Image.open(image_path)
            decoded_objects = decode(img_pil)
            for obj in decoded_objects:
                logging.info(f"Pyzbar detected: {obj.data.decode('utf-8')}")
                return obj.data.decode("utf-8")
        except Exception as e:
            logging.error(f"Pyzbar error: {e}")

    # Method 3: OpenCV (Fallback)
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        bd = cv2.barcode.BarcodeDetector()
        retval, decoded_info, decoded_type, points = bd.detectAndDecode(img)
        
        if retval:
            if isinstance(decoded_info, (tuple, list)):
                 for code in decoded_info:
                     if code: 
                        logging.info(f"OpenCV detected: {code}")
                        return code
            elif isinstance(decoded_info, str) and decoded_info:
                logging.info(f"OpenCV detected: {decoded_info}")
                return decoded_info
                
    except Exception as e:
        logging.error(f"OpenCV barcode error: {e}")
        
    return None
