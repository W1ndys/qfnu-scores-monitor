import ddddocr
from utils.logger import setup_logger

logger = setup_logger()
ocr = ddddocr.DdddOcr(show_ad=False)


def get_ocr_res(cap_pic_bytes):
    """
    识别验证码
    参数:
        cap_pic_bytes: 验证码图片数据
    返回:
        识别结果字符串，失败返回 None
    """
    try:
        res = ocr.classification(cap_pic_bytes)
        if res and len(res) > 0:
            return res
        return None
    except Exception as e:
        logger.warning(f"OCR识别出错: {str(e)}")
        return None


if __name__ == "__main__":
    get_ocr_res("123")
