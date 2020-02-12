package beam.competition.inputs.framework

import java.nio.file.Path

import com.github.martincooper.datatable.{DataColumn, DataTable}
import com.github.tototoshi.csv.{CSVFormat, CSVReader, QUOTE_MINIMAL, Quoting}
import com.typesafe.scalalogging.LazyLogging

import scala.collection.immutable
import scala.reflect.ClassTag
import scala.reflect.io.File
import scala.util.Try

object StringCol

case class InputReader(inputRoot: String) extends LazyLogging {

  def readInput[I <: Input : ClassTag](inputDataHelper: InputDataHelper[I]): Seq[I] = {
    readCsvInput(inputDataHelper)
  }

  private def readCsvInput[I <: Input : ClassTag](inputDataHelper: InputDataHelper[I]): Seq[I] = {
    // Automatically resolve input file by convention
    val inputFileName = File(inputRoot) / s"${inputDataHelper.name.stripSuffix("Input")}.csv"

    val csvFormat: CSVFormat = new CSVFormat {
      override val delimiter: Char = ','
      override val quoteChar: Char = '"'
      override val escapeChar: Char = '\\'
      override val lineTerminator: String = "\n"
      override val quoting: Quoting = QUOTE_MINIMAL
      override val treatEmptyLineAsNil: Boolean = true
    }

    val reader = CSVReader.open(inputFileName.toString())(csvFormat)

    val df: DataTable = InputReader.readDataTableForFields(inputDataHelper.fields, reader, inputDataHelper.getClass.getSimpleName)
    inputDataHelper.convertDataTable(df)
  }

}

object InputReader {

  def loadDblDataTable(fields: Map[String, Object], path: Path, name: String): DataTable = {
    val reader = CSVReader.open(path.toString)
    val dblFields = fields.map { case (k, _) => k -> Double }
    InputReader.readDataTableForFields(dblFields, reader, name)
  }

  def readDataTableForFields(fields: Map[String, Object], reader: CSVReader, name: String): DataTable = {
    val rows: immutable.Seq[Map[String, String]] = reader.allWithHeaders()
    reader.close()
    val columns = fields.keys.map { k => (k, rows map { row => row.getOrElse(k, "0.0") }) }
    val data = columns map { case (k, v) => fields(k) match {
      case StringCol => new DataColumn[String](k, v)
      case Int => new DataColumn[Int](k, v map { x => Try(x.toInt).toOption.getOrElse(0) })
      case Double => new DataColumn[Double](k, v map { x => Try(x.toDouble).toOption.getOrElse(0.0) })
    }
    }
    DataTable(name, data).get
  }
}
