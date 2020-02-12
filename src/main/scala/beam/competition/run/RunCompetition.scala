package beam.competition.run


object RunCompetition extends CompetitionHelper {

  def main(args: Array[String]): Unit = {

    runCompetition(args)
    logger.info("Exiting BISTRO")
    System.exit(0)
  }
}
