//package beam.competition.aicrowd
//
//import com.redis._
//
//class RedisManager {
//  /**
//   * Class to handle all interactions with the message broker
//   */
//
//  private var redisClientPool: RedisClientPool = _
//  private var REDIS_HOST: String = _
//  private var REDIS_PORT: Int = _
//  private var REDIS_DB : Int = _
//  private var REDIS_PASSWORD : Option[Any] = _
//  // TODO: Add support for Redis Password
//
//  private var updateFrequency : Long =  5 * 1000 // Every 5 seconds
//  private var lastUpdateTime : Long = System.currentTimeMillis - updateFrequency - 1000;
//  // Initialise the lastUpdateTime in the past, to ensure that the first sync is definitely relayed
//
//  initializeRedisConnection()
//
//  /**
//   * If necessary :
//   * Initializes message-broker (Redis) connection by looking up the correct Environment
//   * variables.
//   *
//   * List of Expected Environment Variables
//   *
//   * - AICROWD_SYNC_STATE_WITH_REDIS :
//   * 				If set, the evaluator knows that we expect the Run state to be dumped into a redis instance
//   * 				If this value is not set, then all the Redis related interactions are silently ignored.
//   * - AICROWD_REDIS_HOST
//   * 				Host of the redis instance (Default : localhost)
//   * - AICROWD_REDIS_PORT
//   * 				Port of the redis instance (Default : 6379)
//   * - AICROWD_REDIS_DB
//   * 				Database number of the redis instance (Default : 0)
//   * - AICROWD_REDIS_PASSWORD
//   *        AUTH Password of the redis instance (Default : None)
//   * - AICROWD_EVALUATION_RUN_NAME
//   * 				A unique name for the said run of the evaluation. This is also used as the key in which
//   * 				the Run state is stored.
//   *
//   */
//  def initializeRedisConnection(): Unit = {
//    if(System.getenv("AICROWD_SYNC_STATE_WITH_REDIS") != null ){
//
//      // Gather Redis coordinates from relevant Environment variables
//      REDIS_HOST = scala.util.Properties.envOrElse("AICROWD_REDIS_HOST", "localhost")
//      REDIS_PORT = scala.util.Properties.envOrElse("AICROWD_REDIS_PORT", "6379").toInt
//      REDIS_DB = scala.util.Properties.envOrElse("AICROWD_REDIS_DB", "0").toInt
//      REDIS_PASSWORD = scala.util.Properties.envOrNone("AICROWD_REDIS_PASSWORD")
//
//      redisClientPool = new RedisClientPool(
//            host = REDIS_HOST,
//            port = REDIS_PORT,
//            database = REDIS_DB,
//            secret = REDIS_PASSWORD
//            )
//
//      // Run a test operation to ensure that the connection is established
//      redisClientPool.withClient {
//        client => {
//          client.send[String]("PING")("PONG") match {
//            case "PONG" => Console.println("Connected to Redis Server...")
//            case _ => throw new Exception("Unable to connect to Redis Server :( ")
//          }
//        }
//      }
//    }else{
//      // Silently Ignore
//      Console.println("Warning : Ignoring intialisation of Message Broker as required Environment Variables are not present")
//    }
//  }
//
//  /**
//   * Syncs the Run state with Redis after picking up the
//   * expected keys, etc from the correct Environment variables.
//   */
//  def syncRunStateWithRedis(payload: String, forceUpdate: Boolean = false): Unit = {
//    if(System.getenv("AICROWD_SYNC_STATE_WITH_REDIS")!= null){
//
//      if(forceUpdate || System.currentTimeMillis - lastUpdateTime > updateFrequency){
//        redisClientPool.withClient {
//          client => {
//            client.set(
//                 scala.util.Properties.envOrElse("AICROWD_EVALUATION_RUN_NAME", "AICROWD_BEAM_EVALUATION_RUN"),
//                 payload
//            )
//          }
//        }
//        lastUpdateTime = System.currentTimeMillis
//      }
//    }else{
//      // Silently Ignore When the correct ENV variables are not set.
//      // A warning is anyway printed during initialization
//    }
//  }
//
//}
