from mlops.tracking import setup_mlflow, log_document_processing


def test_mlflow_tracking_setup():
    setup_mlflow()


def test_mlflow_document_processing_logging():
    log_document_processing(
        document_type="Employee Report",
        word_count=10,
        status="verified"
    )
