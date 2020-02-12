package beam.competition.aicrowd


import com.typesafe.config.Config

/**
  * Monitors and Maintains the Run state during a single simulation
  */
case class RunStateMonitor(s3OutputLoc: Option[String]=None) {
  private var config: Config = _
  var numberOfIterations: Int = _
  var runState: RunState = _

  var redisManager: RedisManager = new RedisManager()

  /**
    * @constructor instantiates the evaluation state
    * @param config Configuration object for the current simulation
    */
  def init(config: Config): Unit = {
    this.numberOfIterations = config.getInt("matsim.modules.controler.lastIteration") + 1
    this.config = config
    instantiateRunState()
  }

  /**
    * Instantiates the evaluation state
    */
  def instantiateRunState(): Unit = {
    runState = new RunState(this.config)
    syncStateWithRedis()
    //debug();
  }

  /**
    * Debug function
    */
  def debug(): Unit = {
    runState.state = RunStateTemplates.IN_PROGRESS
    runState.progress = 1.0
    runState.score = 123

    Console.println(runState.iterations.length)
    Console.println(runState.serialize(prettyPrint = true))
  }

  /**
    * Sets the current iteration
    */
  def setCurrentIteration(iteration: Int): Unit = {
    runState.current_iteration = iteration
    syncStateWithRedis()
  }

  /**
    * Sets the overall run state
    */
  def setState(state: String): Unit = {
    runState.state = state
    syncStateWithRedis()
  }

  /**
    * Sets the overall run score
    */
  def setScore(score: Double): Unit = {
    runState.score = score
  }

  /**
    * Sets the overall run progress
    */
  def setProgress(progress: Double): Unit = {
    runState.progress = progress
    syncStateWithRedis()

    if (progress > 0) {
      setState(RunStateTemplates.IN_PROGRESS)
      syncStateWithRedis()
    }
  }

  /**
    * Sets the run state of an iteration
    */
  def setIterationState(iterationIdx: Int, state: String): Unit = {
    runState.iterations(iterationIdx).state = state
    syncStateWithRedis()
  }

  /**
    * Sets the progress of an iteration
    */
  def setIterationProgress(iterationIdx: Int, progress: Double): Unit = {
    runState.iterations(iterationIdx).progress = progress
    syncStateWithRedis()
  }

  /**
    * Zips and uploads the output dump from a single run to S3
    * if the following Env variables are provided :
    * AWS_ACCESS_KEY_ID
    * AWS_SECRET_ACCESS_KEY
    * AWS_BUCKET_NAME
    * AWS_FILE_KEY_TEMPLATE
    *
    */
  def uploadOutputDump(outputFolder: String): Unit = {
    val s3FileKey: String = OutputProcessor.compressAndUploadToS3(outputFolder,s3OutputLoc)
    runState.output_dump_s3_key = s3FileKey
  }

  /**
    * Serializes the evaluation state
    */
  def serializeState(prettyPrint: Boolean = false): String = {
    runState.serialize(prettyPrint)
  }

  /**
    * If necessary :
    * Syncs the evaluation state with Redis after picking up the
    * expected keys, etc from the correct Environment variables.
    */
  def syncStateWithRedis(forceUpdate: Boolean = false): Unit = {
    redisManager.syncRunStateWithRedis(
      serializeState(),
      forceUpdate
    )
  }

}
