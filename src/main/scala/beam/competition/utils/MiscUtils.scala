package beam.competition.utils

import java.io.FileOutputStream
import java.nio.file.Path
import java.util.UUID
import java.util.UUID._

import beam.competition.visualization.SpatialConversion.CoordPair
import better.files.{File => ScalaFile}
import com.conveyal.r5.transit.TransportNetwork
import org.apache.commons.compress.utils.IOUtils
import org.geojson.LngLatAlt
import org.matsim.api.core.v01.Coord
import org.matsim.api.core.v01.population.{Activity, Person}

import java.io.{FileInputStream, IOException}

import org.apache.commons.compress.archivers.tar.{TarArchiveEntry, TarArchiveOutputStream}


import scala.collection.JavaConverters

object MiscUtils {
  def getNumberOfLegsInPlan(p: Person): Int =
    JavaConverters
      .iterableAsScalaIterable(p.getSelectedPlan.getPlanElements)
      .count { pe =>
        pe.isInstanceOf[Activity]
      }

  def moveInputs(src: Path, dest: Path): Unit = {
    if (src.toFile.list().isEmpty)
      throw new IllegalArgumentException("Input folder is empty.")
    org.apache.commons.io.FileUtils
      .copyDirectory(src.toAbsolutePath.toFile, dest.toFile)
  }

  def getR5EdgeCoords(linkId: Int)(implicit transportNetwork: TransportNetwork): CoordPair = {
    val currentEdge = transportNetwork.streetLayer.edgeStore.getCursor(linkId)
    val coords = currentEdge.getGeometry.getCoordinates
    val startCoord = new Coord(coords(0).x, coords(0).y)
    val endCoord = new Coord(coords(1).x, coords(1).y)
    CoordPair(startCoord, endCoord)
  }

  def getCoordsAsLineString(tupleCoords: CoordPair): org.geojson.LineString = {
    val startLatLngAlt = new LngLatAlt(tupleCoords.first.getX, tupleCoords.first.getY)
    val endLatLngAlt = new LngLatAlt(tupleCoords.second.getX, tupleCoords.second.getY)
    new org.geojson.LineString(startLatLngAlt, endLatLngAlt)
  }

  import org.apache.commons.compress.archivers.tar.TarArchiveOutputStream


  def archiveFolder(root: ScalaFile): ScalaFile = {
    val destFile = ScalaFile(s"/tmp/${randomUUID().toString}.tar")
    val taos: TarArchiveOutputStream = new TarArchiveOutputStream(new FileOutputStream(destFile.toString()))
    taos.setLongFileMode(TarArchiveOutputStream.LONGFILE_GNU)
    recurseFiles(root, root, taos)
    taos.finish()
    taos.flush()
    taos.close()

    destFile
  }

  /**
    * Recursive traversal to add files
    *
    * @param root
    * @param taos
    * @throws IOException
    */
  @throws[IOException]
  private def recurseFiles(root: ScalaFile, file: ScalaFile, taos: TarArchiveOutputStream) {
    if (file.isDirectory) {
      for {
        f <- file.list
      } recurseFiles(root, f, taos)
    } else if (!file.name.endsWith(".tar") && (!file.name.endsWith(".TAR"))) {
      val filename =
        file.toJava.getAbsolutePath().substring(root.toJava.getAbsolutePath.length())
      val tae = new TarArchiveEntry(filename)
      tae.setSize(file.size)
      taos.putArchiveEntry(tae)
      val fis = new FileInputStream(file.toJava)
      IOUtils.copy(fis, taos)
      taos.closeArchiveEntry()
    }
  }

}
