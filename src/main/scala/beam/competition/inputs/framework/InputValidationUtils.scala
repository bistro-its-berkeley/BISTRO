package beam.competition.inputs.framework

import beam.competition.run.CompetitionServices
import beam.competition.utils.LoggingUtils
import beam.sim.common.{Range => CensusRange}
import com.google.common.collect.{RangeSet, TreeRangeSet, Range => GuavaRange}
import ch.qos.logback.classic.Level
import com.typesafe.scalalogging.LazyLogging
import com.wix.accord.Descriptions.Explicit
import com.wix.accord.Violation


import scala.collection.JavaConverters._
import scala.collection.mutable


trait InputValidationUtils extends LazyLogging {

  implicit val competitionServices: CompetitionServices

  LoggingUtils.createFileLogger(competitionServices.OUTPUT_DIRECTORY, classOf[InputProcessor].getName,
    Level.ERROR)

  def logViolations(className: String, violations: Set[Violation]) {
    logger.error(s"In the $className, validation failed when checking the following item(s):")
    violations.foreach { violation => logger.error(formatErrorMessage(violation)) }
  }

  private[this] def formatErrorMessage(violation: Violation): String = {

    val description = violation.path.headOption match {
      case Some(Explicit(d)) => d
      case None => "that a rule was violated"
    }

    s"\t* $description; ${formatConstraint(violation.constraint)}"
  }

  private[this] def formatConstraint(constraint: String): String = {
    constraint match {
      case "must be true" => "this constraint was violated."
      case a: String => a
    }
  }
}

object InputValidationUtils {

  /** Check if gaps between range endpoints exceed the minimum limit.
    *
    * For example, this predicate returns `false` for the following pair of successive ranges:
    * "(11,20) [21,26).
    *
    *
    * @param ranges sequence of ranges defined in input file
    * @return `false` if the sequence of [[CensusRange ranges]] contains gaps, `true` otherwise
    */
  def createsNoImplicitCoverageGaps(ranges: List[CensusRange], censusIndicator: CensusIndicator): Boolean = {
    ranges.sortBy(_.lowerBound).sliding(2).forall({ rangePair =>
      if (rangePair.size < 2) true else if (rangePair.head.upperBound == censusIndicator.minValue && rangePair.last.lowerBound == censusIndicator.minValue) {
        true
      } else if (rangePair.last.lowerBound == censusIndicator.maxValue && rangePair.head.upperBound == censusIndicator.maxValue) {
        true
      } else if (rangePair.last.equals(rangePair.head)) {
        true
      }else if(rangePair.last.lowerBound-rangePair.head.upperBound == 1){
        true
      }
      else (rangePair.last.lowerBound - rangePair.head.upperBound) >= censusIndicator.minInterval
    })
  }

  implicit def cRange2GRange(censusRange:CensusRange):GuavaRange[Integer]={
    GuavaRange.closed(censusRange.lowerBound,censusRange.upperBound)
  }


  def coalesceCRange(ranges:Set[CensusRange]):mutable.Set[CensusRange]={
    val rangeSet: RangeSet[Integer] = TreeRangeSet.create[Integer]
    ranges.foreach{rangeSet.add(_)}
    rangeSet.asDescendingSetOfRanges().asScala.map(x=>
      CensusRange(s"[${x.lowerEndpoint()}:${x.upperEndpoint()}]"))
  }

  //
//  def createsViolatingOverlappingApplications(rangeAmounts: Seq[CensusBasedAllocation], limit: Int): Boolean = {
//    // census ranges closed in implementation
//    rangeAmounts.foreach { case (amt, cr) => {
//
//      (amt, grange)
//    })
//    }
//  }

  case class CensusBasedAllocation(censusIndicatorRange: Map[CensusIndicator,CensusRange], amount: Float){

    def getScalaRanges:Set[Range]={
     censusIndicatorRange.map{case(_,crange)=>crange.lowerBound to crange.upperBound}.toSet
   }

  }



}
