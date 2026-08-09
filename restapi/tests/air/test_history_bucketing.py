from datetime import timedelta

import pytest

from restapi.air.postgres_repository import HISTORY_TARGET_POINTS, bucket_width_for_range


@pytest.mark.parametrize(
    "span",
    [
        timedelta(hours=1),
        timedelta(hours=24),
        timedelta(days=7),
        timedelta(days=30),
        timedelta(days=3650),
    ],
)
def test_bucket_width_for_range_always_yields_the_target_point_count(span):
    width = bucket_width_for_range(span)
    assert span / width == pytest.approx(HISTORY_TARGET_POINTS)


def test_bucket_width_for_range_never_goes_below_the_nodes_own_reading_interval():
    assert bucket_width_for_range(timedelta(seconds=1)) == timedelta(seconds=30)


def test_bucket_width_for_range_scales_proportionally_with_the_span():
    assert bucket_width_for_range(timedelta(hours=48)) == bucket_width_for_range(timedelta(hours=24)) * 2
