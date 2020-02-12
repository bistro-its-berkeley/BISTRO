package beam

import java.io.File

import com.github.martincooper.datatable.DataTable
import com.github.tototoshi.csv.CSVWriter

package object competition {

  val competitionFileDirRoot = "competition"

  /**
    * Allows for [[DataTable df]] save [[File file]] type syntax
    *
    * @param df A [[DataTable data table]]
    */
  implicit class DataTableSaver(df: DataTable) {
    lazy val writer: CSVWriter.type = CSVWriter


    def save(where: File): String = {
      val openWriter = writer.open(where)
      openWriter.writeRow(df.columns.map {
        _.name
      })
      df.foreach { r => openWriter.writeRow(r.values) }
      openWriter.close()
    where.toString
    }
  }

  def sleep(time: Long) { Thread.sleep(time) }

}
