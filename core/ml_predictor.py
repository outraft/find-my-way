import random

class TrafficPredictor:
	def __init__(self):
		# Add model.pkl if it exists
		pass

	def predict_delay_factor(self, hour: int) -> float:
		"""
		Returns a multiplier for travel based on hour of day.
		1 -> Normal speed
		1.5 -> %50 slower (since traffic = istanbul)
		"""

		if 7 <= hour <= 9 or 17 <= hour <= 20:
			return 1.5
		elif 0 <= hour <= 5:
			return 0.5
		else:
			return 1

		# TODO: Add a sklearn or a XGBoost to here to analize traffic even further


predictor = TrafficPredictor()