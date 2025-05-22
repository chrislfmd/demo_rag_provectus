import json, boto3, os
import great_expectations as ge
s3 = boto3.client("s3")

def handler(event, _ctx):
    # event will contain bucket/key written by Textract in next steps
    bucket = event["bucket"]
    key    = event["key"]

    obj = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    data = json.loads(obj)

    df = ge.dataset.PandasDataset(data["Blocks"])
    df.expect_column_values_to_not_be_null("Text")
    result = df.validate()
    if not result.success:
        raise ValueError("DQ failed")

    return event  # pass-through
