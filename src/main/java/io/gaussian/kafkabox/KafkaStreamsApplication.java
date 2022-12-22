package io.gaussian.kafkabox;

import io.gaussian.kafkabox.utils.Util;
import org.apache.kafka.clients.admin.NewTopic;
import org.apache.kafka.common.serialization.Serde;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.Topology;
import org.apache.kafka.streams.kstream.Consumed;
import org.apache.kafka.streams.kstream.Produced;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URISyntaxException;
import java.net.URL;
import java.util.Arrays;
import java.util.Optional;
import java.util.Properties;
import java.util.concurrent.CountDownLatch;

import static java.util.Arrays.asList;

public class KafkaStreamsApplication {

    private static final Logger logger = LoggerFactory.getLogger(KafkaStreamsApplication.class);

    private static void runKafkaStreams(final KafkaStreams streams) {
        final CountDownLatch latch = new CountDownLatch(1);
        streams.setStateListener((newState, oldState) -> {
            if (oldState == KafkaStreams.State.RUNNING && newState != KafkaStreams.State.RUNNING) {
                latch.countDown();
            }
        });

        streams.start();

        try {
            latch.await();
        } catch (final InterruptedException e) {
            throw new RuntimeException(e);
        }

        logger.info("Streams Closed");
    }

    private static Topology buildTopology(String inputTopic, String outputTopic) {
        Serde<String> stringSerde = Serdes.String();

        StreamsBuilder builder = new StreamsBuilder();

        builder
                .stream(inputTopic, Consumed.with(stringSerde, stringSerde))
                .peek((k, v) -> logger.info("Observed event: {}", v))
                .mapValues(s -> s.toUpperCase())
                .peek((k, v) -> logger.info("Transformed event: {}", v))
                .to(outputTopic, Produced.with(stringSerde, stringSerde));

        return builder.build();
    }

    private static File getFileFromResource() throws URISyntaxException {
        URL resource = KafkaStreamsApplication.class.getClassLoader().getResource("dev.properties");
        if (resource == null) {
            throw new IllegalArgumentException("file not found!");
        } else {

            // failed if files have whitespaces or special characters
            //return new File(resource.getFile());

            return new File(resource.toURI());
        }
    }

    private static Properties getConfig() throws URISyntaxException {
        Properties prop = new Properties();
        try (InputStream input = new FileInputStream(getFileFromResource())) {
            prop.load(input);
        } catch (IOException ex) {
            ex.printStackTrace();
        }
        return prop;
    }

    public static void main(String[] args) throws Exception {
        final Properties config = getConfig();
        final String inputTopic = config.getProperty("input.topic.name");
        final String outputTopic = config.getProperty("output.topic.name");

        try (Util utility = new Util()) {

            utility.createTopics(
                    config,
                    asList(
                            new NewTopic(inputTopic, Optional.empty(), Optional.empty()),
                            new NewTopic(outputTopic, Optional.empty(), Optional.empty())));

            try (Util.Randomizer rando = utility.startNewRandomizer(config, inputTopic)) {

                KafkaStreams kafkaStreams = new KafkaStreams(
                        buildTopology(inputTopic, outputTopic),
                        config);

                Runtime.getRuntime().addShutdownHook(new Thread(kafkaStreams::close));

                logger.info("Kafka Streams 101 App Started");
                runKafkaStreams(kafkaStreams);

            }
        }
    }
}
