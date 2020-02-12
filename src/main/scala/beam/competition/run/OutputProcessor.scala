package beam.competition.aicrowd

import java.nio.file.Paths
import java.util.UUID.randomUUID

import awscala._
import awscala.s3._
import better.files.{File => ScalaFile}
import cats.implicits._
import com.amazonaws.services.s3.model.ObjectMetadata
import com.typesafe.scalalogging.LazyLogging

import scala.sys.process._

/**
  * Processes the final output folders
  */
object OutputProcessor extends LazyLogging {

  /**
    * Compresses a file into a single gz or tar.gz file depending
    * on whether or not it is a folder.
    */
  def compress(outputFilePath: String): String = {
    val file: ScalaFile = ScalaFile(outputFilePath)
    file.zipTo(ScalaFile(s"/tmp/${file.name}.zip")).toString()
  }

  def runPostProcessing(beamOutputFolderPath: String, iterNum: Int, s3OutputKeyOpt: Option[String], sampleSize: String): Unit = {
    if (System.getenv("AWS_ACCESS_KEY_ID") != null) {
      val RANDOM_SEARCH_NUM: String = scala.util.Properties.envOrElse("RANDOM_SEARCH_ID", "false")
      val s3DestKeyArg = s"--s3_dest_key=${s3OutputKeyOpt.get}"
      val randomSearchArg = if (!RANDOM_SEARCH_NUM.contains("false")) {
        s"--random_search_num=$RANDOM_SEARCH_NUM"
      } else {
        ""
      }
      s"python3 post_processing/beam_events_processing.py --output_dir=$beamOutputFolderPath --iter_number=$iterNum --sample_size=$sampleSize $randomSearchArg $s3DestKeyArg" ! ProcessLogger(stderr append _)
    }
  }

  /**
    * Compresses the BEAM output folder and uploads it to S3
    *
    * @param beamOutputFolderPath path to BEAM simulation output folder
    * @param s3OutputKeyOpt       used to specify sub-bucket (during for e.g., random search). If [[None]], then archive will be zipped and stored in default location, else will be stored in specified location as a tar.gz file.
    * @return path on S3 as [[String]]
    */
  def compressAndUploadToS3(beamOutputFolderPath: String, s3OutputKeyOpt: Option[String] = None): String = {
    s3OutputKeyOpt match {
      case Some(s3OutputLoc) =>
        val toUpload = if (ScalaFile(beamOutputFolderPath).isDirectory)
          compress(beamOutputFolderPath)
        else beamOutputFolderPath
        uploadToS3(toUpload, s3OutputLoc)
      case None =>
        uploadToS3(compress(beamOutputFolderPath), "%s")
    }
  }

  /**
    * Uploads a file to S3 at a particular location
    */
  private def uploadToS3(outputDumpPath: String, s3OutputLoc: String): String = {
    Console.println("Uploading file to S3...")
    if (System.getenv("AWS_ACCESS_KEY_ID") != null) {
      val AWS_ACCESS_KEY_ID: String = scala.util.Properties.envOrElse("AWS_ACCESS_KEY_ID", "false")
      val AWS_SECRET_ACCESS_KEY: String = scala.util.Properties.envOrElse("AWS_SECRET_ACCESS_KEY", "false")
      val AWS_BUCKET_NAME: String = scala.util.Properties.envOrElse("AWS_BUCKET_NAME", "false")
      val AWS_FILE_KEY_TEMPLATE: String = scala.util.Properties.envOrElse("AWS_FILE_KEY_TEMPLATE", "false")
      val RANDOM_SEARCH_ID: String = scala.util.Properties.envOrElse("RANDOM_SEARCH_ID", "false")

      val prefix = if (!RANDOM_SEARCH_ID.equals("false")) {
        Paths.get(AWS_FILE_KEY_TEMPLATE, if (RANDOM_SEARCH_ID.equals("-1")) {
          ""
        } else {
          s"Exploration_$RANDOM_SEARCH_ID"
        }, s"$s3OutputLoc").toString
      } else {
        s""
      }
      //
      // The bucket that is configured to store the submission outputs
      // should be configured to allow new public ACLs and uploading public objects
      //
      // Bucket > Permissions > Public Access Settings > Edit > <All False>
      implicit val region: Region = Region.US_WEST_2
      val credentialsProvider = new BasicCredentialsProvider(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
      implicit val s3: S3 = S3(credentialsProvider)
      val bucket: Option[Bucket] = s3.bucket(AWS_BUCKET_NAME)
      import com.amazonaws.services.s3.S3ClientOptions
      val clientOptions = new S3ClientOptions()
      clientOptions.setChunkedEncodingDisabled(true)
      clientOptions.setPathStyleAccess(false)
      s3.setS3ClientOptions(clientOptions)
      val extension = ScalaFile(outputDumpPath).extension(includeDot = true, includeAll = true)

      (bucket, extension).mapN { case (_bucket, ext) =>
        val suff = if(ext.contains("zip")){
          randomUUID()
        } else{
          ScalaFile(outputDumpPath).nameWithoutExtension(includeAll = true)
        }
        val dumpFileKey: String = s"output/results-$suff$ext"
        val s3DestKey = s"$prefix/$dumpFileKey"
        val objectMetaData = new ObjectMetadata()
        objectMetaData.setContentLength(ScalaFile(outputDumpPath).size)
        logger.error(s"Dest Key: $s3DestKey")
        logger.info("Target Key : " + dumpFileKey)
        _bucket.putObject(s3DestKey, ScalaFile(outputDumpPath).newInputStream,objectMetaData)

        // Clean up the outputDump path:
        ScalaFile(outputDumpPath).delete(true)
        s3DestKey
      }.get
    } else {
      //Clean up the outputDump path:
      ScalaFile(outputDumpPath).delete(true)
      logger.info("Warning: Ignoring uploading of the outputdump to S3 because of the lack of the relevant Environment variables.")
      "false"
    }
  }

}
