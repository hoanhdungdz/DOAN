import { useEffect, useState } from "react";
import { api, errorText } from "./api";

export default function useRemote(path, revision = 0) {
  const [state, setState] = useState({
    path,
    revision,
    data: null,
    loading: true,
    error: "",
  });
  useEffect(() => {
    let live = true;
    setState({ path, revision, data: null, loading: true, error: "" });
    api(path)
      .then((data) => {
        if (live) setState({ path, revision, data, loading: false, error: "" });
      })
      .catch((error) => {
        if (live)
          setState({
            path,
            revision,
            data: null,
            loading: false,
            error: errorText(error),
          });
      });
    return () => {
      live = false;
    };
  }, [path, revision]);
  // List and detail routes may reuse a component. Never render the previous
  // response shape while React is waiting to run the next effect.
  return state.path === path && state.revision === revision
    ? state
    : { data: null, loading: true, error: "" };
}
