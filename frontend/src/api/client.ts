/** The only way the UI talks to the API: the generated client over the committed OpenAPI document (spec 13.4). */

import createFetchClient from "openapi-fetch";
import createQueryClient from "openapi-react-query";
import type { paths } from "@/api/schema";

export const fetchClient = createFetchClient<paths>({ baseUrl: window.location.origin });

export const api = createQueryClient(fetchClient);
