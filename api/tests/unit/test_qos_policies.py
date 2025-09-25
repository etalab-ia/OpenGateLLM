from api.clients.model.qos_policies import ParallelRequestsThresholdPolicy, PerformanceThresholdPolicy


class TestParallelRequestsThresholdPolicy:
    def test_allows_when_under_limit(self):
        policy = ParallelRequestsThresholdPolicy(max_parallel_requests=5)
        assert policy.apply_policy(performance_indicator=None, current_parallel_requests=3)

    def test_allows_when_equal_to_limit(self):
        policy = ParallelRequestsThresholdPolicy(max_parallel_requests=5)
        assert policy.apply_policy(performance_indicator=None, current_parallel_requests=5)

    def test_rejects_when_above_limit(self):
        policy = ParallelRequestsThresholdPolicy(max_parallel_requests=5)
        assert not policy.apply_policy(performance_indicator=None, current_parallel_requests=6)

    def test_allows_when_current_is_none(self):
        policy = ParallelRequestsThresholdPolicy(max_parallel_requests=5)
        assert policy.apply_policy(performance_indicator=None, current_parallel_requests=None)


class TestPerformanceThresholdPolicy:
    def test_allows_when_under_threshold(self):
        policy = PerformanceThresholdPolicy(performance_threshold=0.8)
        assert policy.apply_policy(performance_indicator=0.5, current_parallel_requests=None)

    def test_allows_when_equal_to_threshold(self):
        policy = PerformanceThresholdPolicy(performance_threshold=0.8)
        assert policy.apply_policy(performance_indicator=0.8, current_parallel_requests=None)

    def test_rejects_when_above_threshold(self):
        policy = PerformanceThresholdPolicy(performance_threshold=0.8)
        assert not policy.apply_policy(performance_indicator=0.9, current_parallel_requests=None)

    def test_allows_when_performance_is_none(self):
        policy = PerformanceThresholdPolicy(performance_threshold=0.8)
        assert policy.apply_policy(performance_indicator=None, current_parallel_requests=None)
