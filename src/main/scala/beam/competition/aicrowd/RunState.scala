package beam.competition.aicrowd

import com.typesafe.config.Config
import org.json4s.JsonDSL._
import org.json4s.native.JsonMethods._

import scala.collection.mutable.ArrayBuffer

/**
  * Monitors and Maintains the evaluation state during a single simulation
  */
class RunState {
  private var config: Config = _
  var numberOfIterations: Int = _
  

  var iterations: ArrayBuffer[IterationState] = ArrayBuffer[IterationState]()
  
  var _current_iteration: Int = 0
  var _state: String = RunStateTemplates.PENDING
  var _progress: Double = 0.0
  var _score: Double = 0.0
  var _output_dump_s3_key = "N/A"

  /**
    * @constructor instantiates the evaluation state
    * @param config Configuration object for the current simulation
    */
  def this(config: Config) = {
    this()
    this.numberOfIterations = config.getInt("matsim.modules.controler.lastIteration") + 1
    this.config = config
    instantiateRunState()
  }

  /**
    * Instantiates the iteration states for all
    */
  def instantiateRunState(): Unit = {
    (1 to numberOfIterations).foreach{_=>iterations.append(new IterationState())}
  }

  // Getter / Setters for `current_iteration`
  def current_iteration: Int = _current_iteration

  def current_iteration_=(value: Int): Unit = {
    _current_iteration = value
  }

  // Getter / Setters for `state`
  def state: String = _state

  def state_=(value: String): Unit = {
    if (!RunStateTemplates.VALID_STATES.contains(value)) {
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

  // Getter / Setters for `output_dump_s3_key`
  def output_dump_s3_key: String = _output_dump_s3_key

  def output_dump_s3_key_=(value: String): Unit = {
    _output_dump_s3_key = value
  }

  // Getter / Setters for `score`
  def score: Double = _score

  def score_=(value: Double): Unit = {
    _score = value
  }

  def get_git_head: String = {
    scala.util.Properties.envOrElse("GIT_HEAD", "na");
  }

  /**
    * Serialize the RunState into a valid JSON
    *
    * @param prettyPrint Boolean parameter which controls if the rendered JSON
    *                    should be compact or pretty-printed.
    */
  def serialize(prettyPrint: Boolean = false): String = {
    // Aggregate data into Schema
    val json =
      ("timestamp" -> System.currentTimeMillis) ~
        ("state" -> state) ~
        ("progress" -> progress) ~
        ("score" -> score) ~
        ("output_dump_s3_key" -> output_dump_s3_key) ~
        ("current_iteration" -> (current_iteration + 1)) ~
        ("total_iterations" -> numberOfIterations) ~
        ("git_head" -> get_git_head)
        // ("iterations" ->
        //   iterations.map { iter =>
        //     ("state" -> iter.state) ~
        //       ("progress" -> iter.progress)
        //   })

    // Render the data
    if (prettyPrint) {
      pretty(render(json))
    } else {
      compact(render(json))
    }
  }
}

object RunStateTemplates {
  val PENDING = "PENDING"
  val IN_PROGRESS = "IN_PROGRESS"
  val SUCCESS = "SUCCESS"
  val ERROR = "ERROR"

  val VALID_STATES = List(PENDING, IN_PROGRESS, SUCCESS, ERROR)
}
