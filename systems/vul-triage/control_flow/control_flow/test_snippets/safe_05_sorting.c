/*
 * safe_05_sorting.c
 * 安全的排序算法实现 —— 无漏洞
 * 数组固定大小，所有索引均经过边界验证。
 */
#include <stdio.h>

#define ARRAY_SIZE 20

void swap(int *a, int *b) {
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

/* 插入排序 */
void insertion_sort(int arr[], int n) {
    for (int i = 1; i < n; i++) {
        int key = arr[i];
        int j = i - 1;
        while (j >= 0 && arr[j] > key) {
            arr[j + 1] = arr[j];
            j--;
        }
        arr[j + 1] = key;
    }
}

/* 选择排序 */
void selection_sort(int arr[], int n) {
    for (int i = 0; i < n - 1; i++) {
        int min_idx = i;
        for (int j = i + 1; j < n; j++) {
            if (arr[j] < arr[min_idx]) {
                min_idx = j;
            }
        }
        if (min_idx != i) {
            swap(&arr[i], &arr[min_idx]);
        }
    }
}

/* 二分查找（前提：已排序） */
int binary_search(const int arr[], int n, int target) {
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}

void print_array(const int arr[], int n) {
    for (int i = 0; i < n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
}

int main(void) {
    int data1[ARRAY_SIZE] = {39, 12, 7, 45, 2, 88, 16, 55, 33, 21,
                             90, 4, 67, 11, 73, 28, 50, 19, 61, 8};
    int data2[ARRAY_SIZE];
    for (int i = 0; i < ARRAY_SIZE; i++) data2[i] = data1[i];

    printf("Original:  "); print_array(data1, ARRAY_SIZE);

    insertion_sort(data1, ARRAY_SIZE);
    printf("Insertion: "); print_array(data1, ARRAY_SIZE);

    selection_sort(data2, ARRAY_SIZE);
    printf("Selection: "); print_array(data2, ARRAY_SIZE);

    int idx = binary_search(data1, ARRAY_SIZE, 45);
    printf("Search 45: index=%d\n", idx);

    idx = binary_search(data1, ARRAY_SIZE, 99);
    printf("Search 99: index=%d\n", idx);

    return 0;
}
