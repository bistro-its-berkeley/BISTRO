package beam.competition.aicrowd

/**
  * Monitors and Maintains the Iteration state during a single iteration
  *
  */
class IterationState() {
  private var _state: String = IterationStateTemplates.PENDING
  private var _progress: Double = 0.0

  // Getter / Setters for `state`
  def state: String = _state

  def state_=(value: String): Unit = {
    if (!IterationStateTemplates.VALID_STATES.contains(value)) {
      throw new Exception("Invalid iteration state provided : %s".format(value))
    }
    _state = value
  }

  // Getter / Setters for `progress`
  def progress: Double = _progress

  def progress_=(value: Double): Unit = {
    if (value < 0.0 || value > 1.0) {
      throw new Exception(
        """
           Invalid iteration progress value provided : %f.
           Iteration Progress Values have to be in the range [0,1].
           """.format(value))
    }
    _progress = value
  }
}

object IterationStateTemplates {
  val PENDING = "PENDING"
  val IN_PROGRESS = "IN_PROGRESS"
  val SUCCESS = "SUCCESS"
  val ERROR = "ERROR"

  val VALID_STATES = List(PENDING, IN_PROGRESS, SUCCESS, ERROR)
}
