from datetime import UTC, datetime, timedelta, timezone

import pytest

from api.domain import BaseModel, UtcDatetime


class Entity(BaseModel):
    moment: UtcDatetime
    optional_moment: UtcDatetime | None = None


class TestUtcDatetime:
    def test_should_keep_an_utc_datetime_unchanged(self):
        # Arrange
        moment = datetime(2026, 8, 27, 12, 30, tzinfo=UTC)

        # Act
        entity = Entity(moment=moment)

        # Assert
        assert entity.moment == moment
        assert entity.moment.tzinfo == UTC

    def test_should_read_a_naive_datetime_as_utc(self):
        # Act
        entity = Entity(moment=datetime(2026, 8, 27, 12, 30))

        # Assert
        assert entity.moment == datetime(2026, 8, 27, 12, 30, tzinfo=UTC)

    def test_should_convert_an_offset_datetime_to_utc(self):
        # Arrange
        moment = datetime(2026, 8, 27, 14, 30, tzinfo=timezone(timedelta(hours=2)))

        # Act
        entity = Entity(moment=moment)

        # Assert
        assert entity.moment == datetime(2026, 8, 27, 12, 30, tzinfo=UTC)
        assert entity.moment.tzinfo == UTC

    def test_should_read_an_unix_timestamp_as_utc(self):
        # Arrange
        moment = datetime(2026, 8, 27, 12, 30, tzinfo=UTC)

        # Act
        entity = Entity(moment=int(moment.timestamp()))

        # Assert
        assert entity.moment == moment

    def test_should_round_trip_to_the_same_unix_timestamp(self):
        # Arrange
        timestamp = 1_756_298_000

        # Act
        entity = Entity(moment=timestamp)

        # Assert
        assert int(entity.moment.timestamp()) == timestamp

    def test_should_allow_none_on_an_optional_field(self):
        # Act
        entity = Entity(moment=datetime(2026, 8, 27, tzinfo=UTC), optional_moment=None)

        # Assert
        assert entity.optional_moment is None

    def test_should_reject_a_value_that_is_not_a_datetime(self):
        # Act & Assert
        with pytest.raises(ValueError):
            Entity(moment="not-a-datetime")
