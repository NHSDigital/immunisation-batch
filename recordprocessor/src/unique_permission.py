import pandas as pd
import boto3
from io import StringIO


def get_unique_action_flags_from_s3(bucket_name, key):
    """
    Reads the CSV file from an S3 bucket and returns a set of unique ACTION_FLAG values.
    """
    s3_client = boto3.client('s3')
    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    csv_content = response['Body'].read().decode('utf-8')

    # Load content into a pandas DataFrame
    df = pd.read_csv(StringIO(csv_content), usecols=["ACTION_FLAG"])
    print(f"dataframe:{df}")
    # Get unique ACTION_FLAG values in one step
    unique_action_flags = set(df["ACTION_FLAG"].str.upper().unique())
    print(f"unique_action_flags:{unique_action_flags}")
    return unique_action_flags
