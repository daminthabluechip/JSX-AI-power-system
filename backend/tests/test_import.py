import io

HEADER = "customer,address,latitude,longitude,weight_kg,volume_m3,priority,target_date,earliest_arrival,latest_arrival"
GOOD = "Fresh Mart,12 Galle Rd,6.91,79.85,850,4.5,high,2026-10-14,08:00,12:00"
GOOD2 = "City Pharma,45 Kandy Rd,7.27,80.60,300,1.2,critical,2026-10-14,09:00,15:00"


def post_csv(client, text, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return client.post(f"/orders/import?{q}", data=text.encode("utf-8"), content_type="text/csv")


def test_import_creates_orders(client):
    res = post_csv(client, "\n".join([HEADER, GOOD, GOOD2]))
    assert res.status_code == 201 and res.get_json()["created"] == 2
    orders = client.get("/orders?per_page=10").get_json()["items"]
    assert {o["customer"] for o in orders} == {"Fresh Mart", "City Pharma"}
    assert next(o for o in orders if o["customer"] == "City Pharma")["priority"] == "critical"


def test_one_bad_row_rejects_the_whole_file_with_row_numbers(client):
    bad = "Broken,x,not-a-number,79.8,-5,1,urgent,2026-10-14,15:00,09:00"
    res = post_csv(client, "\n".join([HEADER, GOOD, bad]))
    body = res.get_json()
    assert res.status_code == 400 and body["created"] == 0 and body["skipped"] == 1
    assert body["errors"][0]["row"] == 3
    fields = body["errors"][0]["errors"]
    assert {"latitude", "weight_kg", "priority"} <= set(fields)
    assert client.get("/orders").get_json()["total"] == 0


def test_skip_invalid_saves_the_good_rows(client):
    bad = "Broken,x,6.9,79.8,0,1,low,2026-10-14,,"
    res = post_csv(client, "\n".join([HEADER, GOOD, bad, GOOD2]), skip_invalid="true")
    body = res.get_json()
    assert res.status_code == 201 and body["created"] == 2 and body["skipped"] == 1
    assert body["errors"][0]["row"] == 3 and "weight_kg" in body["errors"][0]["errors"]


def test_optional_columns_blank_lines_case_and_excel_bom(client):
    text = "\ufeff" + "Customer, ADDRESS ,Latitude,Longitude,Weight_kg,Volume_m3,Target_Date\n" \
           "ACME,1 Road,6.9,79.8,100,1,2026-10-14\n\n   ,,,,,,\n"
    res = client.post("/orders/import", data=text.encode("utf-8"), content_type="text/csv")
    assert res.status_code == 201 and res.get_json()["created"] == 1
    order = client.get("/orders").get_json()["items"][0]
    assert order["priority"] == "medium" and order["earliest_arrival"] is None


def test_missing_columns_and_empty_file_and_non_utf8(client):
    res = post_csv(client, "customer,address\nACME,1 Road")
    assert res.status_code == 400 and "missing columns" in res.get_json()["details"]["file"]
    assert post_csv(client, "").status_code == 400
    assert client.post("/orders/import", data=b"\xff\xfe\x00bad", content_type="text/csv").status_code == 400


def test_multipart_file_upload_and_template(client):
    res = client.post("/orders/import", data={"file": (io.BytesIO("\n".join([HEADER, GOOD]).encode()), "orders.csv")},
                      content_type="multipart/form-data")
    assert res.status_code == 201 and res.get_json()["created"] == 1

    tpl = client.get("/orders/import/template")
    assert tpl.mimetype == "text/csv" and tpl.get_data(as_text=True).startswith("customer,address,latitude")
    assert post_csv(client, tpl.get_data(as_text=True)).get_json()["created"] == 2
