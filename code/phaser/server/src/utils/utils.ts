import _ from "lodash";
export function findDifferences(prevState: any, currState: any) {
  return _.transform(
    currState,
    (result: { [x: string]: any }, value: any, key: string | number) => {
      if (!_.isEqual(value, prevState[key])) {
        result[key] =
          _.isObject(value) && _.isObject(prevState[key])
            ? findDifferences(prevState[key], value)
            : value;
      }
    }
  );
}

export function shuffleArray<T>(array: T[]): T[] {
  // return array; // Disable shuffling for now
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]]; // Swap elements
  }
  return array;
}

export function arraysContainSameItems(
  arr1: number[],
  arr2: number[]
): boolean {
  if (arr1.length !== arr2.length) {
    return false;
  }

  // Compare the sorted arrays
  for (let i = 0; i < arr1.length; i++) {
    // Check if arr2 contains the element
    if (arr2.indexOf(arr1[i]) === -1) {
      return false;
    }
  }
  return true;
}
