import pandas as pd
import numpy as np
import logging
import sys

logger = logging.getLogger("gatekeeper")

def verify_model_integrity(predict_fn, feature_cols):
    """
    Runs a mock prediction on a 1-row DataFrame to ensure the closure is valid
    and all dependencies are met.
    """
    logger.info("--- [GATEKEEPER] Verifying Model Integrity ---")
    try:
        # 1. Create dummy data
        dummy_data = pd.DataFrame(
            np.random.normal(0, 1, size=(10, len(feature_cols))),
            columns=feature_cols
        )
        dummy_data["id"] = [f"id_{i}" for i in range(10)]
        dummy_data["era"] = "0001"
        
        # 2. Execute prediction
        logger.info("Executing mock prediction on %d features...", len(feature_cols))
        result = predict_fn(dummy_data)
        
        # 3. Validate output format
        if not isinstance(result, pd.DataFrame):
            raise TypeError(f"Predict function returned {type(result)}, expected pd.DataFrame")
        
        if "prediction" not in result.columns:
            raise KeyError("Predict function output missing 'prediction' column")
        
        if result["prediction"].isna().any():
            raise ValueError("Predict function returned NaNs in predictions")

        logger.info("[PASS] Integrity check successful.")
        return True

    except Exception as e:
        logger.error("[FAIL] Model Integrity Check Failed: %s", e)
        # Detailed diagnostic output
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Test the gatekeeper itself
    logging.basicConfig(level=logging.INFO)
    def mock_bad_fn(df): return "not a dataframe"
    def mock_good_fn(df): return pd.DataFrame({"id": df["id"], "prediction": [0.5]*len(df)})
    
    print("\nTesting Bad Function:")
    verify_model_integrity(mock_bad_fn, ["f1", "f2"])
    
    print("\nTesting Good Function:")
    verify_model_integrity(mock_good_fn, ["f1", "f2"])
