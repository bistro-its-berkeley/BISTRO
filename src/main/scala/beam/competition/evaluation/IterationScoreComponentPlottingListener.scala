package beam.competition.evaluation

import java.io.{BufferedWriter, File, FileWriter}
import java.nio.file.{Files, Paths}
import java.util.StringJoiner

import beam.analysis.plots.{GraphUtils, GraphsStatsAgentSimEventsListener}
import beam.competition.evaluation.evaluator.SubmissionEvaluatorFactory
import beam.competition.run.CompetitionServices
import com.google.inject.Inject
import com.typesafe.scalalogging.LazyLogging
import org.jfree.data.category.DefaultCategoryDataset
import org.matsim.core.controler.events.IterationEndsEvent
import org.matsim.core.controler.listener.IterationEndsListener

import scala.collection.mutable
import scala.collection.mutable.ListBuffer

case class IterationScoreComponentPlottingListener @Inject()(submissionEvaluatorFactory: SubmissionEvaluatorFactory)(implicit val competitionServices: CompetitionServices) extends IterationEndsListener with LazyLogging {

  private val iterationSummaryStats: ListBuffer[Map[java.lang.String, java.lang.Double]] = ListBuffer()
  private val graphFileNameDirectory: mutable.Map[String, Int] = mutable.Map[String, Int]()
  private val summaryData = new mutable.HashMap[String, mutable.Map[Int, Double]]()

  override def notifyIterationEnds(event: IterationEndsEvent): Unit = {
    val submissionEvaluator = submissionEvaluatorFactory.getEvaluatorForIteration(event.getIteration)
    val result = submissionEvaluator.scoreSubmission()
    val scoreSummaryMap = submissionEvaluator.getRawScoreSummaryMap

    iterationSummaryStats += scoreSummaryMap
    val summaryStatsFile = Paths.get(event.getServices.getControlerIO.getOutputFilename(CompetitionServices.COMPETITION_ROOT), "rawScores.csv").toFile

    writeSummaryStats(summaryStatsFile)
    iterationSummaryStats.flatMap(_.keySet).distinct.foreach { x =>
      val key = x.split("_")(0)
      val value = graphFileNameDirectory.getOrElse(key, 0) + 1
      graphFileNameDirectory += key -> value
    }

    val fileNames = iterationSummaryStats.flatMap(_.keySet).distinct.sorted
    fileNames.foreach(file => createSummaryStatsGraph(file, event.getIteration))
    graphFileNameDirectory.clear()


    logger.info(result.toString())
  }

  private def createSummaryStatsGraph(fileName: String, iteration: Int): Unit = {
    val fileNamePath =
      competitionServices.beamServices.matsimServices.getControlerIO.getOutputFilename(fileName.replaceAll("[/: ]", "_") + ".png")
    val index = fileNamePath.lastIndexOf("/")
    val outDir = new File(fileNamePath.substring(0, index) + "/summaryStats/rawScores")
    val directoryName = fileName.split(":")(0)
    val numberOfGraphs: Int = 10
    val directoryKeySet = graphFileNameDirectory.filter(_._2 >= numberOfGraphs).keySet

    if (!outDir.exists()) {
      Files.createDirectories(outDir.toPath)
    }

    if (directoryKeySet.contains(directoryName)) {
      directoryKeySet foreach { file =>
        if (file.equals(directoryName)) {
          val dir = new File(outDir.getPath + "/" + file)
          if (!dir.exists()) {
            Files.createDirectories(dir.toPath)
          }
          val path = dir.getPath + fileNamePath.substring(index)
          createGraph(iteration, fileName, path)
        }
      }
    } else {
      val path = outDir.getPath + fileNamePath.substring(index)
      createGraph(iteration, fileName, path)
    }

  }

  private def createGraph(iteration: Int, fileName: String, path: String): Unit = {
    val doubleOpt = iterationSummaryStats(iteration).get(fileName)
    val value: Double = doubleOpt.getOrElse(0.0).asInstanceOf[Double]

    val dataset = new DefaultCategoryDataset

    var data = summaryData.getOrElse(fileName, new mutable.TreeMap[Int, Double])
    data += (iteration -> value)
    summaryData += fileName -> data

    val updateData = summaryData.getOrElse(fileName, new mutable.TreeMap[Int, Double])

    updateData.foreach(x => dataset.addValue(x._2, 0, x._1))
    val sj = new StringJoiner(" ")

    val fileNameTokens = fileName.replaceAll("[:/ ]", "_").split("_")
    fileNameTokens.takeWhile(!_.equals("")).foreach(sj.add(_))
    var header = sj.toString
    if (fileNameTokens.size > 1) {
      header = header + " - " + fileNameTokens.slice(header.split(" ").size, fileNameTokens.size).mkString(" ") + ""
    }

    val chart = GraphUtils.createStackedBarChartWithDefaultSettings(
      dataset,
      header,
      "iteration",
      header,
      path,
      false
    )

    GraphUtils.saveJFreeChartAsPNG(
      chart,
      path,
      GraphsStatsAgentSimEventsListener.GRAPH_WIDTH,
      GraphsStatsAgentSimEventsListener.GRAPH_HEIGHT
    )
  }

  private def writeSummaryStats(summaryStatsFile: File): Unit = {
    val keys = iterationSummaryStats.flatMap(_.keySet).distinct.sorted

    val out = new BufferedWriter(new FileWriter(summaryStatsFile))
    out.write("Iteration,")
    out.write(keys.mkString(","))
    out.newLine()

    iterationSummaryStats.zipWithIndex.foreach {
      case (stats, it) =>
        out.write(s"$it,")
        out.write(
          keys
            .map { key =>
              stats.getOrElse(key, 0)
            }
            .mkString(",")
        )
        out.newLine()
    }

    out.close()
  }

}
