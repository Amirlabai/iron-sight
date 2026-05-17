from src.utils import config


class TestConfigConstants:
    def test_should_expose_tactical_threshold_constants(self):
        assert config.MIN_IRAN_THRESHOLD == 35
        assert config.MAX_IRAN_THRESHOLD == 50

    def test_should_expose_inflation_factors(self):
        assert config.DEFAULT_INFLATION_FACTOR == 1.0
        assert config.DRONE_INFLATION_FACTOR == 1.5
        assert config.MISSILE_INFLATION_FACTOR == 1.25

    def test_should_use_asia_jerusalem_timezone(self):
        assert str(config.TIMEZONE) == "Asia/Jerusalem"
