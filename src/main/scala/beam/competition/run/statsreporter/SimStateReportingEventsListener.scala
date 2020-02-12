
package beam.competition.run.statsreporter

import beam.competition.aicrowd._
import beam.sim.BeamServices
import org.matsim.api.core.v01.events.Event
import org.matsim.core.events.handler.BasicEventHandler

class SimStateReportingEventsListener(beamServices: BeamServices, esMonitor: RunStateMonitor) extends BasicEventHandler {

  // private val statsFactory = new StatsFactory(beamServices)
  private val runStateMonitor: RunStateMonitor = esMonitor

  private var currentIteration: Int = 0
  private var overallProgress: Double = 0.0
  private var currentIterationProgress: Double = 0.0
  private val MINIMUM_PROGRESS_UPDATE_THRESHOLD: Double = 0.2
  private var lastIterationProgressSnapshot: Double = 0.0

  override def handleEvent(event: Event): Unit = {
    // Register Progress event here

    currentIterationProgress = Math.min(event.getTime / 3600 / 30, 1.0)
    // Only update the RunState Monitor after there has been a minimum progress update (of 20% / 0.2)
    // Hence only a total of ~5 updates per iteration
    if (currentIterationProgress - lastIterationProgressSnapshot > MINIMUM_PROGRESS_UPDATE_THRESHOLD) {

      runStateMonitor.setIterationProgress(currentIteration, currentIterationProgress)

      overallProgress = (currentIteration + currentIterationProgress) / runStateMonitor.runState.numberOfIterations
      runStateMonitor.setProgress(overallProgress)
      lastIterationProgressSnapshot = currentIterationProgress
    }

  }

  override def reset(iteration: Int) {
    // Register beginning of iteration here
    currentIteration = iteration

    if (currentIteration > 0) {
      //Mark the previous iteration as COMPLETE
      runStateMonitor.setIterationState(currentIteration - 1, IterationStateTemplates.SUCCESS)
    }
    // Mark the current iteration as IN_PROGRESS
    runStateMonitor.setIterationState(currentIteration, IterationStateTemplates.IN_PROGRESS)
    runStateMonitor.setCurrentIteration(currentIteration)

    // Reset counters
    lastIterationProgressSnapshot = 0.0
    currentIterationProgress = 0.0
  }



} 
