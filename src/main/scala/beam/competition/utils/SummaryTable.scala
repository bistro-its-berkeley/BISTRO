package beam.competition.utils

import java.io.PrintStream

import beam.competition.evaluation.component.NormalizedScoreComponent
import org.matsim.core.utils.io.IOUtils

import scala.collection.mutable.ListBuffer

case class SummaryTable() {

  val header: Seq[String] = Seq("Component Name", "Weight", "Z-Mean", "Z-StdDev", "Raw Score", "Weighted Score")

  var rows: ListBuffer[Seq[String]] = ListBuffer.empty

  def addRow(rowData: (String, String, String, String, String, String)): Unit = {
    rows += Seq(rowData._1, rowData._2, rowData._3, rowData._4, rowData._5, rowData._6)
  }

  def addRow(scoreComponent: NormalizedScoreComponent): Double = {
    addRow(scoreComponent.scoreComponentWeightIdentifier.longName, scoreComponent.weight.toString, scoreComponent.standardizationParams.mu.toString, scoreComponent.standardizationParams.sigma.toString, scoreComponent.rawScore.toString, scoreComponent.ans.toString)
    scoreComponent.ans
  }

  def reset(): Unit = {
    rows.clear()
  }

  def outputSummaryTable(outputFile: String): Unit = {

    val fileStream: PrintStream = IOUtils.getPrintStream(outputFile)

    (header +: rows).map(_.foldRight("")((a, b) => s"$a,$b").dropRight(1)) foreach fileStream.println

    fileStream.flush()

    fileStream.close()
  }

  def getScoreSummaryMap: Map[String, java.lang.Double] = {

    (for{row<-rows if row.tail.reverse(1).nonEmpty}yield{row.head->row.tail.reverse(1).toDouble.asInstanceOf[java.lang.Double]}).toMap
  }

}
