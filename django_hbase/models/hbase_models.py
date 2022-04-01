from django_hbase.hbase_client import HBaseClient
from django_hbase.models.constants import INTEGER_FIELD_LENGTH
from django_hbase.models.exceptions import (
    EmptyRowKeyException,
    RowKeyNotInitializedException,
    RowKeyNotDefinedException,
    EmptyDataException,
    EmptyColumnDataException,
    FieldTypeException,
    BadColumnKeyException,
)
from django_hbase.models.hbase_fields import HBaseField


class HBaseModel:

    class Meta:
        table_name = None
        row_key = ()

    def __init__(self, **kwargs):
        class_fields = self.get_class_fields()
        for key, field in class_fields.items():
            value = kwargs.get(key)
            if value is None:
                value = field.default
            if value is None and field.is_required:
                raise EmptyColumnDataException(f"{key} is required.")
            if value is None:
                continue
            setattr(self, key, value)

    @classmethod
    def get_table(cls):
        if cls.Meta.table_name is None:
            raise NotImplementedError('The table name is not specified.')
        conn = HBaseClient.get_connection()
        table = conn.table(cls.Meta.table_name)
        return table

    @classmethod
    def get_class_fields(cls):
        values = {}
        for key, value in cls.__dict__.items():
            if isinstance(value, HBaseField):
                values[key] = value
        return values

    @classmethod
    def serialize_field_to_str(cls, field, field_data):
        if field is None or field_data is None:
            return None
        str_value = str(field_data)
        if field.data_type == 'int':
            str_value = str(field_data)
            while len(str_value) < INTEGER_FIELD_LENGTH:
                str_value = '0' + str_value
            if field.reverse:
                str_value = str_value[::-1]
        if field.data_type == 'timestamp':
            value = int(field_data)
            str_value = str(value)
        return str_value

    @classmethod
    def deserialize_field(cls, field, str_value):
        value = None
        if field.data_type == 'int':
            if field.reverse:
                str_value = str_value[::-1]
            value = int(str_value)
        if field.data_type == 'timestamp':
            value = int(str_value)
        if field.data_type != 'int' and field.data_type != 'timestamp':
            raise FieldTypeException(f'{field.data_type} is not implemented')
        return value

    @classmethod
    def serialize_row_key(cls, instance_fields):
        """
        fields_data is the instance.__dict__: map<String, value>
        """
        if not cls.Meta.row_key:
            raise EmptyRowKeyException("The row key is not specified.")
        values = []
        class_fields = cls.get_class_fields()
        for key in cls.Meta.row_key:
            field = class_fields.get(key)
            if field is None:
                raise RowKeyNotDefinedException("The row key is not defined.")
            field_data = instance_fields.get(key)
            if field_data is None:
                raise RowKeyNotInitializedException(f"{key} is not provided.")
            value = cls.serialize_field_to_str(field, field_data)
            values.append(value)
        serialized_row_key = bytes(":".join(values), 'utf-8')
        return serialized_row_key

    @classmethod
    def serialize_row_data(cls, instance_fields):
        """
        return map<bytes, bytes>
        """
        values = {}
        class_fields = cls.get_class_fields()
        for key, field in class_fields.items():
            if field.column_family is None:
                continue
            value = instance_fields.get(key)
            if value is None:
                value = field.default
            if value is None and field.is_required:
                raise EmptyColumnDataException(f"{key} is required.")
            if value is None:
                continue
            if ":" in key:
                raise BadColumnKeyException(": is not allowed in column keys.")
            str_value = cls.serialize_field_to_str(field, value)
            column_key = (field.column_family + ":" + key).encode('utf-8')
            values[column_key] = str_value.encode('utf-8')
        if not values:
            return None
        return values

    @classmethod
    def deserialize_row_data(cls, serialized_row_data):
        """
        return map<key, deserialized_value>
        """
        class_fields = cls.get_class_fields()
        values = {}
        for key, field in class_fields.items():
            if field.column_family is None:
                continue
            column_key = field.column_family + ":" + key
            serialized_value = serialized_row_data.get(column_key.encode('utf-8'))
            if serialized_value is None:
                continue
            value = serialized_value.decode('utf-8')
            deserialized_value = cls.deserialize_field(field, value)
            values[key] = deserialized_value
        return values

    def save(self):
        table = self.get_table()
        serialized_row_key = self.serialize_row_key(self.__dict__)
        serialized_row_data = self.serialize_row_data(self.__dict__)
        if serialized_row_data is None:
            raise EmptyDataException("The column values are not provided.")
        table.put(serialized_row_key, serialized_row_data)

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        instance.save()
        return instance

    @classmethod
    def get(cls, **kwargs):
        """
        only supports querying with row key
        """
        table = cls.get_table()
        serialized_row_key = cls.serialize_row_key(kwargs)
        serialized_row_data = table.row(row=serialized_row_key)
        deserialized_row_data = cls.deserialize_row_data(serialized_row_data)
        instance = cls(**kwargs, **deserialized_row_data)
        return instance

