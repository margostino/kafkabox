import os

from pyspark.sql import SparkSession

jars_folder = "/Library/Frameworks/Python.framework/Versions/3.9/bin/jars"
jars_list = [os.path.join(jars_folder, x) for x in os.listdir(jars_folder)]

spark_jars = ",".join(jars_list)
spark_packages = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.1.2,org.apache.spark:spark-streaming-kafka-0-10_2.12:3.1.2"

spark = SparkSession \
    .builder \
    .appName("test") \
    .config("spark.jars", spark_jars) \
    .config("spark.jars.packages", spark_packages) \
    .master("local[*]") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
# print(spark.sparkContext.getConf().getAll())

columns = ["key", "value"]
data = [("mockk1", "pytest1"), ("mockk2", "pytest2"), ("mockk3", "pytest3")]

df = spark.createDataFrame(data).toDF(*columns)

# df.show()
# df.printSchema()

# BATCH Producer
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
