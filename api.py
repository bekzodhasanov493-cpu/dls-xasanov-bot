from aiohttp import web
import os
import json
import hmac
import hashlib

from dotenv import load_dotenv

from database import get_connection
from config import CARD_NUMBER, CARD_HOLDER


load_dotenv()

HAMYON_API_KEY = os.getenv("HAMYON_API_KEY")


# =========================================================
# DATABASE
# =========================================================

def init_payment_columns():
    conn = get_connection()
    cursor = conn.cursor()

    columns = [
        ("hamyon_invoice_id", "TEXT"),
        ("hamyon_status", "TEXT DEFAULT 'new'"),
        ("payment_amount", "INTEGER DEFAULT 0"),
        ("payment_paid_at", "TEXT"),
    ]

    for column_name, column_type in columns:
        try:
            cursor.execute(
                f"ALTER TABLE ads ADD COLUMN {column_name} {column_type}"
            )
        except Exception:
            pass

    conn.commit()
    conn.close()


# =========================================================
# CORS
# =========================================================

def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = (
        "GET, POST, OPTIONS"
    )
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response


# =========================================================
# GET AD
# =========================================================

async def get_ad(request):
    ad_id = request.match_info["ad_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            ad_fee,
            sale_type,
            price
        FROM ads
        WHERE id = ?
        """,
        (ad_id,)
    )

    ad = cursor.fetchone()

    conn.close()

    if not ad:
        response = web.json_response(
            {
                "ok": False,
                "error": "E'lon topilmadi"
            },
            status=404
        )

        return add_cors_headers(response)

    response = web.json_response(
        {
            "ok": True,
            "ad_id": ad[0],
            "ad_fee": ad[1],
            "sale_type": ad[2],
            "price": ad[3],
            "card_number": CARD_NUMBER,
            "card_holder": CARD_HOLDER
        }
    )

    return add_cors_headers(response)

# =========================================================
# HAMYON REQUEST DATA
# =========================================================

async def read_request_data(request):
    """
    Hamyon JSON yoki form-data yuborsa,
    ikkalasini ham qabul qiladi.
    """

    try:
        if request.content_type == "application/json":
            data = await request.json()

            if isinstance(data, dict):
                return data

        data = await request.post()

        if data:
            return dict(data)

    except Exception:
        pass

    try:
        raw = await request.text()

        if raw:
            try:
                data = json.loads(raw)

                if isinstance(data, dict):
                    return data
            except Exception:
                pass

    except Exception:
        pass

    return {}


# =========================================================
# HAMYON SIGNATURE
# =========================================================

def verify_hamyon_signature(request, body_text):
    """
    Hamyon webhook uchun HMAC tekshiruvi.

    X-Timestamp va X-Signature headerlari mavjud bo‘lsa,
    imzoni tekshiradi.

    Agar headerlar kelmasa, test bosqichida requestni
    qabul qilishga ruxsat beradi.
    """

    if not HAMYON_API_KEY:
        return True

    timestamp = request.headers.get("X-Timestamp")
    signature = request.headers.get("X-Signature")

    if not timestamp or not signature:
        return True

    message = f"{timestamp}.{body_text}"

    expected_signature = hmac.new(
        HAMYON_API_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        signature
    )


# =========================================================
# PREPARE
# =========================================================

async def hamyon_prepare(request):
    body_text = await request.text()

    if not verify_hamyon_signature(
        request,
        body_text
    ):
        response = web.json_response(
            {
                "ok": False,
                "error": "Invalid signature"
            },
            status=401
        )

        return add_cors_headers(response)

    try:
        data = json.loads(body_text)

        if not isinstance(data, dict):
            data = {}

    except Exception:
        data = dict(await request.post())

    print()
    print("========================================")
    print("HAMYON PREPARE")
    print("========================================")
    print(json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    ))
    print("========================================")
    print()

    ad_id = (
        data.get("ad_id")
        or data.get("order_id")
        or data.get("orderId")
    )

    invoice_id = (
        data.get("invoice_id")
        or data.get("invoiceId")
        or data.get("id")
    )

    amount = data.get("amount", 0)

    if ad_id:
        try:
            ad_id_int = int(ad_id)

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE ads
                SET
                    hamyon_invoice_id = ?,
                    hamyon_status = 'prepare',
                    payment_amount = ?
                WHERE id = ?
                """,
                (
                    str(invoice_id)
                    if invoice_id is not None
                    else None,
                    int(amount)
                    if str(amount).isdigit()
                    else 0,
                    ad_id_int
                )
            )

            conn.commit()
            conn.close()

        except Exception as error:
            print(
                "PREPARE database error:",
                error
            )

    response = web.json_response(
        {
            "ok": True
        }
    )

    return add_cors_headers(response)


# =========================================================
# COMPLETE
# =========================================================

async def hamyon_complete(request):
    body_text = await request.text()

    if not verify_hamyon_signature(
        request,
        body_text
    ):
        response = web.json_response(
            {
                "ok": False,
                "error": "Invalid signature"
            },
            status=401
        )

        return add_cors_headers(response)

    try:
        data = json.loads(body_text)

        if not isinstance(data, dict):
            data = {}

    except Exception:
        data = dict(await request.post())

    print()
    print("========================================")
    print("HAMYON COMPLETE")
    print("========================================")
    print(json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    ))
    print("========================================")
    print()

    status = str(
        data.get("status", "")
    ).lower()

    ad_id = (
        data.get("ad_id")
        or data.get("order_id")
        or data.get("orderId")
    )

    invoice_id = (
        data.get("invoice_id")
        or data.get("invoiceId")
        or data.get("id")
    )

    amount = data.get(
        "amount",
        0
    )

    if ad_id:
        try:
            ad_id_int = int(ad_id)

            if status == "paid":
                new_status = "paid"

            elif status == "cancel":
                new_status = "cancel"

            else:
                new_status = status or "unknown"

            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE ads
                SET
                    hamyon_invoice_id = ?,
                    hamyon_status = ?,
                    payment_amount = ?,
                    payment_paid_at =
                        CASE
                            WHEN ? = 'paid'
                            THEN CURRENT_TIMESTAMP
                            ELSE payment_paid_at
                        END
                WHERE id = ?
                """,
                (
                    str(invoice_id)
                    if invoice_id is not None
                    else None,
                    new_status,
                    int(amount)
                    if str(amount).isdigit()
                    else 0,
                    new_status,
                    ad_id_int
                )
            )

            conn.commit()
            conn.close()

            print(
                f"✅ E'lon #{ad_id_int} "
                f"uchun Hamyon status: {new_status}"
            )

        except Exception as error:
            print(
                "COMPLETE database error:",
                error
            )

    response = web.json_response(
        {
            "ok": True
        }
    )

    return add_cors_headers(response)


# =========================================================
# OPTIONS
# =========================================================

async def options_handler(request):
    response = web.Response(
        status=204
    )

    return add_cors_headers(response)


# =========================================================
# HEALTH CHECK
# =========================================================

async def health_check(request):
    response = web.json_response(
        {
            "ok": True,
            "service": "DLS XASANOV API"
        }
    )

    return add_cors_headers(response)


# =========================================================
# APP
# =========================================================

init_payment_columns()

app = web.Application()

# Mini App API
app.router.add_get(
    "/api/ad/{ad_id}",
    get_ad
)

# Hamyon
app.router.add_post(
    "/hamyon/prepare",
    hamyon_prepare
)

app.router.add_post(
    "/hamyon/complete",
    hamyon_complete
)

# OPTIONS / CORS
app.router.add_options(
    "/hamyon/prepare",
    options_handler
)

app.router.add_options(
    "/hamyon/complete",
    options_handler
)

# Health check
app.router.add_get(
    "/health",
    health_check
)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":
    print()
    print("========================================")
    print("DLS | XASANOV API")
    print("========================================")
    print("API:     /api/ad/{ad_id}")
    print("Prepare: /hamyon/prepare")
    print("Complete:/hamyon/complete")
    print("Health:  /health")
    print("========================================")
    print()

    web.run_app(
        app,
        host="0.0.0.0",
        port=8080
    )