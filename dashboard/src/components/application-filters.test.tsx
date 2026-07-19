import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApplicationFilters } from "@/components/application-filters";
import { EMPTY_FILTERS } from "@/lib/metrics";

describe("application filters", () => {
  it("updates search and resets the complete filter model", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <ApplicationFilters
        filters={{ ...EMPTY_FILTERS, site: "jobs.example" }}
        onChange={onChange}
        options={{
          runs: [{ id: "run", label: "Test run" }],
          sites: ["jobs.example"],
          locations: ["Remote"],
          automationStatuses: ["submitted"],
          careerStages: ["applied"],
        }}
        resultCount={12}
      />,
    );

    fireEvent.change(screen.getByLabelText("Search applications"), {
      target: { value: "analyst" },
    });
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ search: "analyst", site: "jobs.example" }),
    );

    await user.click(screen.getByRole("button", { name: "Reset" }));
    expect(onChange).toHaveBeenLastCalledWith(EMPTY_FILTERS);
  });
});
