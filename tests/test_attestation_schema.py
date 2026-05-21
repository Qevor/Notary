from datetime import timedelta

from notary.models.schemas import Prediction, utc_now


def test_prediction_schema_accepts_future_horizon() -> None:
    prediction = Prediction(
        question="Will NOTARY complete the demo?",
        probability=0.8,
        horizon=utc_now() + timedelta(hours=1),
        rationale="The starter code is in place.",
    )
    assert prediction.probability == 0.8

