package beam.competition.inputs.framework

sealed trait CensusIndicator {
  val minValue: Int
  val maxValue: Int
  val minInterval: Int
}

case object Income extends CensusIndicator {
  override val minValue: Int = 0
  override val maxValue: Int = 150000
  override val minInterval: Int = 5000
}

case object Age extends CensusIndicator {
  override val minValue: Int = 1
  override val maxValue: Int = 120
  override val minInterval: Int = 5
}
