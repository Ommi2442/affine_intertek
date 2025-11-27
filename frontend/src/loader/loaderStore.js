import { proxy } from "valtio";

export const loaderStore = proxy({
  loading: false,

  setLoading(value) {
    loaderStore.loading = value;
  }
});
