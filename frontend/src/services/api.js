const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:5000";


export async function apiRequest(
  path,
  options = {}
) {
  const isFormData =
    typeof FormData !== "undefined" &&
    options.body instanceof FormData;

  const headers = {
    ...(options.headers || {}),
  };


  // ========================================================
  // CONTENT TYPE
  // ========================================================
  //
  // For normal JSON requests:
  //     Content-Type = application/json
  //
  // For image/FormData requests:
  //     DO NOT manually set Content-Type.
  //
  // The browser automatically creates the multipart boundary.
  // ========================================================

  if (
    options.body !== undefined &&
    options.body !== null &&
    !isFormData &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] =
      "application/json";
  }


  // ========================================================
  // REQUEST
  // ========================================================

  const response =
    await fetch(
      `${API_BASE_URL}${path}`,
      {
        ...options,

        // Required because EcoLens uses
        // Flask session cookies.
        credentials: "include",

        headers,
      }
    );


  // ========================================================
  // RESPONSE
  // ========================================================

  const contentType =
    response.headers.get(
      "content-type"
    ) || "";

  let payload;


  if (
    contentType.includes(
      "application/json"
    )
  ) {
    payload =
      await response.json();
  } else {
    const text =
      await response.text();

    payload = {
      success: response.ok,
      message: text,
    };
  }


  // ========================================================
  // ERROR
  // ========================================================

  if (!response.ok) {
    const error =
      new Error(
        payload?.error ||
        payload?.message ||
        "Request failed."
      );

    error.status =
      response.status;

    error.data =
      payload;

    throw error;
  }


  return payload;
}


export {
  API_BASE_URL,
};