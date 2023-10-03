import json
import os
from io import BytesIO

import avro
from avro.io import DatumWriter, BinaryEncoder
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, struct, udf
from pyspark.sql.types import StringType, BinaryType


# https://spark.apache.org/docs/latest/structured-streaming-kafka-integration.html#writing-the-output-of-batch-queries-to-kafka


def serialize_to_avro(df, json_format_schema):
    avro_serializer = udf(avro_serialize_udf, BinaryType())
    return (
        df.select(col("key").cast(StringType()), struct(df.columns).alias("struct"))
        .withColumn(
            "value",
            avro_serializer(
                col("struct"),
                lit(json_format_schema),
            ),
        )
        .select("key", "value")
    )


def serialize_to_avro2(df, json_format_schema):
    avro_serializer = udf(avro_serialize_udf2, BinaryType())
    return (
        df.select(col("key").cast(StringType()), struct(df.columns).alias("struct"))
        .withColumn(
            "value",
            avro_serializer(
                col("struct"),
                lit(json_format_schema),
            ),
        )
        .select("key", "value")
    )


def avro_serialize_udf(columns_as_struct, plain_avro_schema):
    def get_non_null_field_type(field_types):
        return [x.type for x in field_types.schemas if x.type != "null"][-1]

    schema = avro.schema.parse(plain_avro_schema)
    # schema_fields_as_dict = {x.name: get_non_null_field_type(field_types=x.type) for x in schema.fields}
    schema_fields_as_dict = {x.name: x.type for x in schema.fields}
    writer = DatumWriter(schema)
    bytes_writer = BytesIO()
    encoder = BinaryEncoder(bytes_writer)
    fields_in_schema = {}
    # print(f"SARLANGA0:  {columns_as_struct.asDict()}")
    # print(f"SARLANGA:  {columns_as_struct.asDict().items()}")
    # SARLANGA:  {'key': 'this_is_key_1', 'value': 'SPADES'}

    value = {
        "metadata": {
            "event_id": "177864ba-6a80-4be1-8f26-4d5800fcecbe",
            "occurred_at": "2023-07-24T12:20:24.938092Z"
        }
    }
    value = json.loads(columns_as_struct.asDict()['value'])
    print(f"SARLANGA: {value}")
    # fields_in_schema["value"] = columns_as_struct.asDict()['value']
    writer.write(value, encoder)
    return bytes_writer.getvalue()


def avro_serialize_udf2(columns_as_struct, plain_avro_schema):
    def get_non_null_field_type(field_types):
        return [x.type for x in field_types.schemas if x.type != "null"][-1]

    schema = avro.schema.parse(plain_avro_schema)
    schema_fields_as_dict = {x.name: get_non_null_field_type(field_types=x.type) for x in schema.fields}
    writer = DatumWriter(schema)
    bytes_writer = BytesIO()
    encoder = BinaryEncoder(bytes_writer)
    fields_in_schema = {}
    for field_name, field_value in columns_as_struct.asDict().items():
        # Deal with the fact that Redshift unload converts booleans values to t for true and f for false
        if field_name not in ["cid", "key", "version", "operation"]:
            final_field_value = field_value
            if field_value is None:
                final_field_value = None
            elif 'boolean' in schema_fields_as_dict[field_name] and not isinstance(field_value, bool):
                final_field_value = True if field_value.lower() in ["t", "true"] else False
            else:
                pass
            fields_in_schema[field_name] = final_field_value
    print(f"SARALIS: {fields_in_schema}")
    # SARALIS: {'value': '{\n  "metadata": {\n    "event_id": "177864ba-6a80-4be1-8f26-4d5800fcecbe",\n    "occurred_at": "2023-07-24T12:20:24.938092Z"\n  }\n}'}
    writer.write(fields_in_schema, encoder)
    return bytes_writer.getvalue()


def create_schema_from_glue_columns(key, name, glue_columns):
    def avro_type_of(type_name):
        glue_table_data_type_to_avro_type = {
            "int": "int",
            "integer": "int",
            "long": "long",
            "bigint": "long",
            "string": "string",
            "boolean": "boolean",
            "double": "double",
        }
        avro_type_name = glue_table_data_type_to_avro_type.get(type_name)
        if not avro_type_name:
            raise ValueError(f"invalid {type_name}. Check the map lib.helpers.glue_table_data_type_to_avro_type and update it with the missing type if necessary")
        return ["null", avro_type_name]

    return str(
        {
            "type": "record",
            "namespace": "org.margostino.batch",
            "name": name.replace("-", "_"),
            "fields": [
                {"name": col_name, "type": avro_type_of(col_type)}
                for col_name, col_type in glue_columns.items()
                if col_name not in [key]
            ],
        }
    ).replace(
        "'", '"'
    )  # Schema needs to have fields with double quotes to be valid


def get_non_null_field_type(field_types):
    return [x.type for x in field_types.schemas if x.type != "null"][-1]


jars_folder = "/Library/Frameworks/Python.framework/Versions/3.9/bin/jars"
jars_list = [os.path.join(jars_folder, x) for x in os.listdir(jars_folder)]

spark_jars = ",".join(jars_list)
spark_packages = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,org.apache.spark:spark-streaming-kafka-0-10_2.12:3.1.2,org.apache.spark:spark-avro_2.12:3.1.2"
# spark_packages = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,org.apache.spark:spark-streaming-kafka-0-10_2.12:3.1.2,org.apache.spark:spark-avro_2.12:3.1.3"

spark = SparkSession \
    .builder \
    .appName("test") \
    .config("spark.jars", spark_jars) \
    .config("spark.jars.packages", spark_packages) \
    .master("local[*]") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
# print(spark.sparkContext.getConf().getAll())

with open("mock1.json", "r") as f:
    mock_value_1 = f.read()
with open("mock2.json", "r") as f:
    mock_value_2 = f.read()
with open("mock3.json", "r") as f:
    mock_value_3 = f.read()

columns = ["key", "value"]
data = [("this_is_key_1", mock_value_1), ("this_is_key_2", mock_value_2), ("this_is_key_3", mock_value_3)]

# df = spark.createDataFrame(data).toDF(*columns)

# json_format_schema = '["null", {"type": "enum", "name": "value", "symbols": ["SPADES", "HEARTS", "DIAMONDS", "CLUBS"]}]'

with open("schema.json", "r") as f:
    json_format_schema = f.read()

# schema = avro.schema.parse(json_format_schema)


# def get_non_null_field_type(field_types):
#     return [x.type for x in field_types.schemas if x.type != "null"][-1]
#
# column_names_from_glue = {
#     "cid": "string",
#     "version": "int",
#     "operation": "string",
#     "value": "string",
# }
# json_format_schema2 = create_schema_from_glue_columns(key="cid",
#                                                       name="some_batch_name_mock",
#                                                       glue_columns=column_names_from_glue)

# schema = avro.schema.parse(json_format_schema)
# schema_fields_as_dict = {x.name: get_non_null_field_type(field_types=x.type) for x in schema.fields}
# {'operation': 'string', 'value': 'string', 'version': 'int'}
print()

# df_avro_value = serialize_to_avro(df, json_format_schema)
# df_avro_value = serialize_to_avro2(df, json_format_schema)
# print(df_avro_value.head(10))
# df_avro_value.printSchema()
print()

# df.show()
# df.printSchema()
data = ['SPADES']
# df = spark.createDataFrame(data, "string")

# d = df.select(col("key").cast("string"), to_avro(struct("value")))
# dft = df.select(col("key").cast("string"), to_avro(df.value, json_format_schema).alias("suite")).collect()
# dft.head()

columns = ["key", "value"]
data = [("this_is_key_1", "juan"), ("this_is_key_2", "ce"), ("this_is_key_3", "pepe")]
df = spark.createDataFrame(data).toDF(*columns)
df.show()
df.printSchema()

# df.select("CAST(value AS STRING)") \
df.select(col("key").cast("string"), col("value")) \
    .write \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9091,localhost:9092") \
    .option("topic", "random-strings") \
    .save(mode="error")

sampleDataframe = (
    spark.read.format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9091,localhost:9092")
    .option("subscribe", "random-strings")
    .load()
)
sampleDataframe.show()

df_consumer = spark \
    .read \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9091,localhost:9092") \
    .option("subscribe", "random-strings") \
    .load()
df_consumer.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)").show()
print()

# BATCH Producer OK
df.selectExpr("CAST(value AS STRING)") \
    .write \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9091,localhost:9092") \
    .option("topic", "random-strings") \
    .save()

# STREAMING Producer
# # kafka_df = df.writeStream \
# # df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)").write \
# #     .format("kafka") \
# #     .option("kafka.bootstrap.servers", "localhost:9091,localhost:9092") \
# #     .option("failOnDataLoss", "false") \
# #     .option("topic", "random-strings") \
# #     .option("checkpointLocation", "./tmp/checkpoint") \
# #     .save()
