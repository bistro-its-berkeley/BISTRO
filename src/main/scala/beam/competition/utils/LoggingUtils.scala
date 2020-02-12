package beam.competition.utils

import ch.qos.logback.classic.encoder.PatternLayoutEncoder
import ch.qos.logback.classic.spi.ILoggingEvent
import ch.qos.logback.classic.{Level, Logger, LoggerContext}
import ch.qos.logback.core.FileAppender
import org.slf4j.LoggerFactory

import scala.reflect.{ClassTag, classTag}

object LoggingUtils {
  /**
    * Creates a File based appender to create a log file in output dir
    * and adds into root logger to put all the logs into output directory
    *
    * @param outputDirectory path of the output directory
    */
  def createFileLogger(outputDirectory: String, className: String, level: Level): Unit = {

    val lc: LoggerContext = LoggerFactory.getILoggerFactory.asInstanceOf[LoggerContext]

    val fileLogger = lc.getLogger(className)

    val ple = new PatternLayoutEncoder
    val pattern = "%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n"
    ple.setPattern(pattern)
    ple.setContext(lc)
    ple.start()

    val fileAppender = new FileAppender[ILoggingEvent]
    fileAppender.setFile(String.format("%s/validation-errors.out", outputDirectory))
    fileAppender.setEncoder(ple)
    fileAppender.setContext(lc)
    fileAppender.start()

    fileLogger.addAppender(fileAppender)
    fileLogger.setLevel(level)

    fileLogger.setAdditive(true) /* set to true if root should log too */
  }

}
