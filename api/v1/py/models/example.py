"""Example model: table definition plus the type conversions of `example`.

Layer: models. This entity exists as a reference: it has one column per common
MySQL data type and shows where each conversion belongs.

- JSON and BLOB are stored in a form MySQL understands and returned in a form
  JSON understands (object/array and base64 string).
- DECIMAL is returned as a string on purpose: converting it to float would lose
  the exact precision the column exists to protect. Money is sent as "12.34".
- tinyint(1) and the date/time types are converted on read so the response
  carries a boolean and an ISO string instead of the raw driver objects.
"""
import base64
import binascii
import json

from models.base_model import BaseModel


class Example(BaseModel):
    TABLE_NAME = 'example'
    ID_COLUMN = 'ExampleId'
    COLUMNS = (
        'ExampleName', 'ExampleCode', 'ExampleDescription', 'ExamplePrice',
        'ExampleQuantity', 'ExampleBigNumber', 'ExampleRatio', 'ExampleActive',
        'ExampleStatus', 'ExampleBirthDate', 'ExampleCreatedAt', 'ExampleStartTime',
        'ExampleYear', 'ExampleMetadata', 'ExamplePicture',
    )

    JSON_COLUMNS = ('ExampleMetadata',)      # stored as text, returned as object/array
    BINARY_COLUMNS = ('ExamplePicture',)     # stored as bytes, returned as base64
    DECIMAL_COLUMNS = ('ExamplePrice',)      # Decimal -> string, never float (keeps precision)
    BOOLEAN_COLUMNS = ('ExampleActive',)     # tinyint(1) -> bool
    DATE_COLUMNS = ('ExampleBirthDate',)     # date -> 'YYYY-MM-DD'
    DATETIME_COLUMNS = ('ExampleCreatedAt',)  # datetime -> 'YYYY-MM-DD HH:MM:SS'
    TIME_COLUMNS = ('ExampleStartTime',)     # timedelta -> 'HH:MM:SS'

    def _filter(self, data):
        """Encode JSON and BLOB values before they reach the database."""
        data = dict(data)
        for column in self.JSON_COLUMNS:
            if data.get(column) is not None:
                data[column] = json.dumps(data[column])
        for column in self.BINARY_COLUMNS:
            if data.get(column) is not None:
                try:
                    data[column] = base64.b64decode(data[column], validate=True)
                except (binascii.Error, ValueError):
                    raise ValueError(f'{column} must be a base64 string')
        return super()._filter(data)

    def _public(self, row):
        """Decode the columns whose driver type is not JSON friendly."""
        row = super()._public(row)
        if row is None:
            return None
        for column in self.JSON_COLUMNS:
            if isinstance(row.get(column), str):
                row[column] = json.loads(row[column])
        for column in self.BINARY_COLUMNS:
            if isinstance(row.get(column), (bytes, bytearray)):
                row[column] = base64.b64encode(bytes(row[column])).decode('ascii')
        for column in self.DECIMAL_COLUMNS:
            if row.get(column) is not None:
                # str(Decimal) keeps every digit the column stores; float would round it
                row[column] = str(row[column])
        for column in self.BOOLEAN_COLUMNS:
            if row.get(column) is not None:
                row[column] = bool(row[column])
        for column in self.DATE_COLUMNS:
            if row.get(column) is not None:
                row[column] = row[column].isoformat()
        for column in self.DATETIME_COLUMNS:
            if row.get(column) is not None:
                row[column] = row[column].isoformat(sep=' ')
        for column in self.TIME_COLUMNS:
            if row.get(column) is not None:
                # MySQL returns a TIME column as timedelta, so format it as HH:MM:SS
                seconds = int(row[column].total_seconds())
                row[column] = f'{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}'
        return row
