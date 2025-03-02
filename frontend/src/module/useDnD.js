import {useVueFlow} from '@vue-flow/core'
import {ref, watch} from 'vue'
import _dagsStore from "@/store/dags";

const dagsStore = _dagsStore()

let id = 0

/**
 * @returns {string} - A unique id.
 */
function getId() {
  return `dndnode_${id++}`
}

/**
 * In a real world scenario you'd want to avoid creating refs in a global scope like this as they might not be cleaned up properly.
 * @type {{draggedType: Ref<string|null>, isDragOver: Ref<boolean>, isDragging: Ref<boolean>}}
 */
const state = {
  /**
   * The type of the node being dragged.
   */
  draggedElement: ref(null),
  draggedType: ref(null),
  isDragOver: ref(false),
  isDragging: ref(false),
  flow: ref(null),
}

export default function useDragAndDrop() {
  const {draggedType, isDragOver, isDragging, draggedElement, flow} = state

  const {addNodes, screenToFlowCoordinate, onNodesInitialized, updateNode} = useVueFlow()

  watch(isDragging, (dragging) => {
    document.body.style.userSelect = dragging ? 'none' : ''
  })

  function onDragStart(event, type) {
    if (event.dataTransfer) {
      event.dataTransfer.setData('application/vueflow', type)
      event.dataTransfer.effectAllowed = 'move'
    }
    draggedElement.value = event

    draggedType.value = type
    isDragging.value = true

    document.addEventListener('drop', onDragEnd)
  }

  /**
   * Handles the drag over event.
   *
   * @param {DragEvent} event
   */
  function onDragOver(event) {
    event.preventDefault()

    if (draggedType.value) {
      isDragOver.value = true

      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'move'
      }
    }
  }

  function onDragLeave() {
    isDragOver.value = false
  }

  function onDragEnd() {
    isDragging.value = false
    isDragOver.value = false
    draggedType.value = null
    console.log('onDragEnd')
    draggedElement.value.srcElement.classList.remove('on_dnd')
    document.removeEventListener('drop', onDragEnd)
  }

  /**
   * Handles the drop event.
   *
   * @param {DragEvent} event
   */
  function onDrop(event) {
    console.log('onDrop')
    draggedElement.value.srcElement.classList.remove('on_dnd')
    console.log(event, draggedElement.value)
    const position = flow.value.screenToFlowCoordinate({
      x: event.clientX - draggedElement.value.offsetX,
      y: event.clientY - draggedElement.value.offsetY,
    })


    dagsStore.addDag(draggedType.value.name, position)

    /**
     * Align node position after drop, so it's centered to the mouse
     *
     * We can hook into events even in a callback, and we can remove the event listener after it's been called.
     **/
    // const {off} = onNodesInitialized(() => {
    //   updateNode(nodeId, (node) => ({
    //     position: {x: node.position.x - node.dimensions.width / 2, y: node.position.y - node.dimensions.height / 2},
    //   }))
    //
    //   off()
    // })
    //
    // addNodes(newNode)
  }

  function dndInit(flowInstance) {
    flow.value = flowInstance
  }

  return {
    draggedType,
    isDragOver,
    isDragging,
    onDragStart,
    onDragLeave,
    onDragOver,
    onDrop,
    dndInit
  }
}
