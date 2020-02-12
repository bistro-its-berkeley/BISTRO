package beam.competition.inputs.impl

import beam.competition.inputs.framework.{Input, InputDataHelper, StringCol}
import beam.competition.run.CompetitionServices
import com.conveyal.gtfs.model.Trip
import com.github.martincooper.datatable.DataTable
import com.wix.accord.dsl._
import com.wix.accord.transform.ValidationTransform

import scala.collection.JavaConverters._
import scala.util.Try


case class FrequencyAdjustmentInput(routeId: String,
                                    startTime: Int,
                                    endTime: Int,
                                    headwaySecs: Int,
                                    exactTimes: Int = 0) extends Input {
  override val id: String = routeId
  val periodLength: Int = endTime - startTime
}

case class FrequencyAdjustmentInputDataHelper()(implicit val competitionServices: CompetitionServices) extends InputDataHelper[FrequencyAdjustmentInput] {

  override val fields: Fields =
    Map("route_id" -> StringCol,
      "start_time" -> StringCol,
      "end_time" -> StringCol,
      "headway_secs" -> StringCol,
      "exact_times" -> StringCol)


  override implicit val inputSeqValidator: ValidationTransform.TransformedValidator[Seq[FrequencyAdjustmentInput]] = validator[Seq[FrequencyAdjustmentInput]] {
    inputSequence =>
      // check fewer than 5 per route
      inputSequence.groupBy {
        _.routeId
      }.values.toVector.map {
        _.size
      }.each as "the number of elements with identical 'route_id's" should be <= 5

      // check not overlapping by route
      inputSequence.groupBy(_.routeId).values.toVector.map(ris => {
        ris.map(ri => (ri.startTime, ri.endTime))
      }).filter(_.size > 1).map {
        hasNoOverlappingPeriods
      }.each as "there must be no overlapping frequency services per 'route_id'" is true
  }

  def hasNoOverlappingPeriods(entryTimes: Seq[(Int, Int)]): Boolean =
    entryTimes.sortBy(_._1).sliding(2).forall { a => {
      val (startA, endA) = a.seq.head
      val (startB, endB) = a.seq.last

      (endA > startA) && (endB > startB) && (startB > endA)
    }
    }

  override implicit val inputValidator: ValidationTransform.TransformedValidator[FrequencyAdjustmentInput] = validator[FrequencyAdjustmentInput] { fa =>
    fa.routeId as "valid route id ('route_id')" is in(competitionServices.gtfsFeeds.flatMap { feed => feed.routes.asScala.keys }.toSet)
    fa.headwaySecs as "headway seconds ('headway_secs')" is within(CompetitionServices.MIN_HEADWAY_SECS until CompetitionServices.MAX_HEADWAY_SECS)
    fa.startTime as "frequency service start time ('start_time')" is between(0 ,86399)
    fa.endTime as "frequency service end time ('end_time')" is between(1 , 86400)
    fa.exactTimes as "the 'exact_time' field" should be < 2
    fa.exactTimes as "the 'exact_time' field" should be > -1
  }

  def getTripForId(tripId: String): Trip = {
    competitionServices.gtfsFeeds.map { feed =>
      feed.trips.asScala(tripId)
    }.head
  }

  override def convertDataTable(dataTable: DataTable): Seq[FrequencyAdjustmentInput] = {
    dataTable.map(
      row =>
        FrequencyAdjustmentInput(
          row("route_id").toString,
          row("start_time").toString.toInt,
          row("end_time").toString.toInt,
          row("headway_secs").toString.toInt,
          Try {
            row("exact_times")
          } match {
            case scala.util.Success(value) => value.asInstanceOf[String].toInt
            case scala.util.Failure(_) => 0
          }))
  }
}
