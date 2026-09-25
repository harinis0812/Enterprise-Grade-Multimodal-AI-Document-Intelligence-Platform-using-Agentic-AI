import os

import mlflow


def setup_mlflow():

    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "mlruns"
    )

    mlflow.set_tracking_uri(
        tracking_uri
    )

    mlflow.set_experiment(
        "DocuAI-Document-Intelligence"
    )


def log_document_processing(
    document_type,
    word_count,
    status
):

    setup_mlflow()

    with mlflow.start_run():

        mlflow.log_param(
            "document_type",
            document_type
        )

        mlflow.log_metric(
            "word_count",
            word_count
        )

        mlflow.set_tag(
            "processing_status",
            status
        )
